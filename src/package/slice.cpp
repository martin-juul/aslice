#include "package/slice.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/manifest.hpp"
#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <string_view>
#include <system_error>
#include <zstd.h>

namespace aslice::package {
namespace {
namespace fs = std::filesystem;
using core::digest;
using core::fields;
using core::Json;
using core::parse_json;
using core::read_bytes;
using core::require;
constexpr std::size_t compressed_limit = 16 * 1024 * 1024;
constexpr std::size_t expanded_limit = 64 * 1024 * 1024;
constexpr std::size_t metadata_limit = 4 * 1024 * 1024;
bool zero(std::string_view text) {
    return text.find_first_not_of('\0') == text.npos;
}
void zcheck(std::size_t status) {
    require(!ZSTD_isError(status), std::string("zstd: ") + ZSTD_getErrorName(status));
}
std::uint64_t octal(std::string_view text) {
    const auto start = text.find_first_not_of(" \0", 0, 2);
    if (start == text.npos) {
        return 0;
    }
    text.remove_prefix(start);
    const auto end = text.find_first_of(" \0", 0, 2);
    if (end != text.npos) {
        require(text.substr(end).find_first_not_of(" \0", 0, 2) == text.npos,
                "invalid tar octal padding");
        text = text.substr(0, end);
    }
    std::uint64_t value = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value, 8);
    require(result.ec == std::errc{} && result.ptr == text.data() + text.size(),
            "invalid tar octal field");
    return value;
}
std::string text_field(std::string_view text) {
    const auto end = text.find('\0');
    if (end == text.npos) {
        return std::string(text);
    }
    require(zero(text.substr(end)), "nonzero tar text padding");
    return std::string(text.substr(0, end));
}
// Entry byte views borrow the decoded archive; retain that string while reading entries.
struct Entry {
    std::string name;
    std::string target;
    char kind;
    std::uint64_t mode;
    std::string_view bytes;
};
// Tar borrows its input for its entire lifetime.
class Tar {
    std::string_view remaining_;

  public:
    explicit Tar(std::string_view bytes) : remaining_(bytes) {}
    Entry next() {
        require(remaining_.size() >= 512 && !zero(remaining_.substr(0, 512)), "missing tar member");
        const auto header = remaining_.substr(0, 512);
        require(header.substr(257, 6) == std::string_view("ustar\0", 6) &&
                    header.substr(263, 2) == "00",
                "only POSIX ustar/pax headers are supported");
        std::uint64_t checksum = 0;
        for (std::size_t i = 0; i < 512; ++i) {
            checksum += i >= 148 && i < 156 ? 32 : static_cast<unsigned char>(header[i]);
        }
        require(checksum == octal(header.substr(148, 8)), "tar header checksum mismatch");
        require(octal(header.substr(108, 8)) == 0 && octal(header.substr(116, 8)) == 0 &&
                    octal(header.substr(136, 12)) == 0 && zero(header.substr(265, 64)),
                "tar ownership and time must be normalized");
        require(zero(header.substr(345)),
                "tar prefix/extension fields are not supported by this inspector");
        require(octal(header.substr(329, 8)) == 0 && octal(header.substr(337, 8)) == 0,
                "tar device fields refused");
        const auto size = octal(header.substr(124, 12));
        require(size <= expanded_limit && size <= remaining_.size() - 512,
                "truncated or oversized tar entry");
        Entry entry{text_field(header.substr(0, 100)), text_field(header.substr(157, 100)),
                    header[156], octal(header.substr(100, 8)),
                    remaining_.substr(512, static_cast<std::size_t>(size))};
        require(entry.mode <= 0777, "special tar mode bits refused");
        require(entry.kind == '0' || entry.kind == '\0' || entry.kind == '5' || entry.kind == '2',
                "tar entry type or pax extension is unsupported");
        if (entry.kind == '\0') {
            entry.kind = '0';
        }
        require(entry.kind == '0' || size == 0, "non-file tar member has contents");
        require(entry.kind == '2' || entry.target.empty(), "unexpected tar link target");
        const auto padded = (static_cast<std::size_t>(size) + 511) / 512 * 512;
        require(padded <= remaining_.size() - 512 &&
                    zero(remaining_.substr(512 + size, padded - size)),
                "invalid tar entry padding");
        remaining_.remove_prefix(512 + padded);
        return entry;
    }
    void finish() const {
        require(remaining_.size() >= 1024 && remaining_.size() % 512 == 0 && zero(remaining_),
                "unexpected tar member or invalid archive ending");
    }
};
void put_octal(std::string& header, std::size_t offset, std::size_t width, std::uint64_t value) {
    std::array<char, 32> buffer{};
    const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value, 8);
    const auto length = static_cast<std::size_t>(result.ptr - buffer.data());
    require(result.ec == std::errc{} && length < width, "tar numeric field overflow");
    header.replace(offset, width - 1, width - 1, '0');
    header.replace(offset + width - 1 - length, length, buffer.data(), length);
}
void append(std::string& tar, const std::string& name, char kind, unsigned mode,
            const std::string& bytes, const std::string& target = {}) {
    require(name.size() <= 100 && target.size() <= 100,
            "long tar names require pax extensions, not yet supported");
    std::string header(512, '\0');
    header.replace(0, name.size(), name);
    put_octal(header, 100, 8, mode);
    put_octal(header, 108, 8, 0);
    put_octal(header, 116, 8, 0);
    put_octal(header, 124, 12, bytes.size());
    put_octal(header, 136, 12, 0);
    header.replace(148, 8, 8, ' ');
    header[156] = kind;
    header.replace(157, target.size(), target);
    header.replace(257, 6, "ustar\0", 6);
    header.replace(263, 2, "00");
    std::uint64_t checksum = 0;
    for (unsigned char byte : header) {
        checksum += byte;
    }
    put_octal(header, 148, 7, checksum);
    header[154] = '\0';
    header[155] = ' ';
    const auto padded = (bytes.size() + 511) / 512 * 512;
    require(tar.size() + 512 + padded <= expanded_limit - 1024,
            "archive exceeds the 64 MiB expanded limit");
    tar += header;
    tar += bytes;
    tar.append(padded - bytes.size(), '\0');
}
std::string decompress(const std::string& blob) {
    require(blob.size() >= 4 && static_cast<unsigned char>(blob[0]) == 0x28 &&
                static_cast<unsigned char>(blob[1]) == 0xb5 &&
                static_cast<unsigned char>(blob[2]) == 0x2f &&
                static_cast<unsigned char>(blob[3]) == 0xfd,
            "expected a standard zstd frame");
    const auto frame_size = ZSTD_findFrameCompressedSize(blob.data(), blob.size());
    zcheck(frame_size);
    require(frame_size == blob.size(), "concatenated frames or trailing compressed bytes refused");
    const auto declared = ZSTD_getFrameContentSize(blob.data(), blob.size());
    require(declared != ZSTD_CONTENTSIZE_ERROR &&
                (declared == ZSTD_CONTENTSIZE_UNKNOWN || declared <= expanded_limit),
            "declared expansion exceeds 64 MiB");
    std::unique_ptr<ZSTD_DCtx, decltype(&ZSTD_freeDCtx)> context(ZSTD_createDCtx(), ZSTD_freeDCtx);
    require(context != nullptr, "cannot allocate zstd context");
    zcheck(ZSTD_DCtx_setParameter(context.get(), ZSTD_d_windowLogMax, 23));
    ZSTD_inBuffer input{blob.data(), blob.size(), 0};
    std::array<char, 65536> buffer{};
    std::string result;
    const auto start = std::chrono::steady_clock::now();
    for (;;) {
        ZSTD_outBuffer output{buffer.data(), buffer.size(), 0};
        const auto before = input.pos;
        const auto status = ZSTD_decompressStream(context.get(), &output, &input);
        zcheck(status);
        require(output.pos <= expanded_limit - result.size(), "expansion exceeds 64 MiB");
        result.append(buffer.data(), output.pos);
        require(std::chrono::steady_clock::now() - start < std::chrono::seconds(5),
                "zstd decoding exceeded five seconds");
        if (status == 0) {
            require(input.pos == input.size, "trailing frame bytes");
            break;
        }
        require(output.pos || input.pos > before, "truncated zstd stream");
    }
    return result;
}
Json descriptor(const Manifest& manifest) {
    return {{"slice_version", 1},
            {"archive", "pax"},
            {"compression", "zstd"},
            {"manifest",
             {{"path", "manifest.json"},
              {"artifact_id", manifest.artifact_id()},
              {"size", manifest.canonical().size()}}},
            {"payload", "payload/"},
            {"payload_entries", manifest.inventory().size()},
            {"payload_bytes", manifest.payload_bytes()}};
}
} // namespace

core::Json inspect_slice_impl(const core::fs::path& file) {
    namespace fs = std::filesystem;
    using core::digest;
    using core::fields;
    using core::Json;
    using core::parse_json;
    using core::read_bytes;
    using core::require;
    const auto blob = aslice::core::take(read_bytes(file, compressed_limit));
    const auto decoded = decompress(blob);
    Tar tar(decoded);
    const auto first = tar.next();
    require(first.name == "slice.json" && first.kind == '0' && first.bytes.size() <= 65536,
            "slice descriptor must be first and at most 64 KiB");
    const auto second = tar.next();
    require(second.name == "manifest.json" && second.kind == '0' &&
                second.bytes.size() <= metadata_limit,
            "manifest must be second and at most 4 MiB");
    const auto manifest =
        core::take(Manifest::parse(aslice::core::take(parse_json(std::string(second.bytes)))));
    require(manifest.canonical() == second.bytes, "manifest is not canonical JSON");
    // Comparing to the reconstructed descriptor checks all fields, types, totals and encoding.
    require(first.bytes == descriptor(manifest).dump(),
            "descriptor is noncanonical or disagrees with manifest");
    const auto root = tar.next();
    require(root.name == "payload/" && root.kind == '5', "payload directory must follow metadata");
    auto files = manifest.inventory();
    std::sort(files.begin(), files.end(), [](const auto& a, const auto& b) {
        return a.path < b.path;
    });
    for (const auto& item : files) {
        const auto entry = tar.next();
        const auto name = item.path;
        const auto kind = item.kind;
        require(entry.name == "payload/" + name && entry.mode == item.mode,
                "archive inventory order/path/mode mismatch");
        require(entry.kind == (kind == "file"        ? '0'
                               : kind == "directory" ? '5'
                                                     : '2'),
                "archive inventory kind mismatch");
        if (kind == "file") {
            require(entry.bytes.size() == item.size &&
                        aslice::core::take(digest(std::string(entry.bytes))) == item.sha256,
                    "archive payload size/hash mismatch");
            for (const auto& relocation : manifest.relocations()) {
                if (relocation.path != name) {
                    continue;
                }
                const auto offset = relocation.offset;
                const auto expected = relocation.expected_hex;
                for (std::size_t i = 0; i < expected.size(); i += 2) {
                    require(static_cast<unsigned char>(entry.bytes[offset + i / 2]) ==
                                std::stoul(expected.substr(i, 2), nullptr, 16),
                            "archive relocation expected bytes mismatch");
                }
            }
        } else if (kind == "symlink") {
            require(entry.target == item.target, "archive symlink target mismatch");
        }
    }
    tar.finish();
    auto result = manifest.inspect();
    result["blob_digest"] = "sha256:" + aslice::core::take(digest(blob));
    result["blob_size"] = blob.size();
    result["container_verified"] = true;
    return result;
}

std::string pack_slice_impl(const Manifest& manifest, const core::fs::path& payload) {
    namespace fs = std::filesystem;
    using core::digest;
    using core::fields;
    using core::Json;
    using core::parse_json;
    using core::read_bytes;
    using core::require;
    require(manifest.canonical().size() <= metadata_limit &&
                manifest.payload_bytes() <= expanded_limit - 1024,
            "manifest/payload exceeds local packing limits");
    aslice::core::take(manifest.verify_payload(payload));
    std::string tar;
    append(tar, "slice.json", '0', 0644, descriptor(manifest).dump());
    append(tar, "manifest.json", '0', 0644, manifest.canonical());
    append(tar, "payload/", '5', 0755, "");
    auto files = manifest.inventory();
    std::sort(files.begin(), files.end(), [](const auto& a, const auto& b) {
        return a.path < b.path;
    });
    for (const auto& file : files) {
        const auto name = file.path;
        const auto kind = file.kind;
        const auto mode = static_cast<unsigned>(file.mode);
        const auto contents =
            kind == "file" ? aslice::core::take(read_bytes(payload / name, expanded_limit)) : "";
        if (kind == "file") {
            require(contents.size() == file.size &&
                        aslice::core::take(digest(contents)) == file.sha256,
                    "payload changed during packing");
        }
        append(tar, "payload/" + name,
               kind == "file"        ? '0'
               : kind == "directory" ? '5'
                                     : '2',
               mode, contents, kind == "symlink" ? file.target : "");
    }
    tar.append(1024, '\0');
    std::string blob(ZSTD_compressBound(tar.size()), '\0');
    const auto size = ZSTD_compress(blob.data(), blob.size(), tar.data(), tar.size(), 3);
    zcheck(size);
    require(size <= compressed_limit, "compressed archive exceeds 16 MiB");
    blob.resize(size);
    return blob;
}

core::Result<core::Json> inspect_slice(const core::fs::path& file) {
    return core::capture([&] {
        return inspect_slice_impl(file);
    });
}

core::Result<std::string> pack_slice(const Manifest& manifest, const core::fs::path& payload) {
    return core::capture([&] {
        return pack_slice_impl(manifest, payload);
    });
}
} // namespace aslice::package
