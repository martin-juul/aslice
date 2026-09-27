#include "package/manifest.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "package/version.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include "tl/expected.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <exception>
#include <filesystem>
#include <map>
#include <memory>
#include <openssl/evp.h>
#include <openssl/types.h>
#include <regex>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace aslice::package {
namespace {
namespace fs = std::filesystem;
using core::digest;
using core::fields;
using core::Json;
using core::require;
constexpr std::size_t metadata_list_limit = 10000;
constexpr std::size_t inventory_entry_limit = 100000;
constexpr std::uint64_t safe_integer = 9007199254740991ULL;
constexpr std::uint64_t payload_limit = 1024ULL * 1024 * 1024;

std::string string(const Json& object, const std::string& name) {
    return object.at(name).get<std::string>();
}
std::uint64_t integer(const Json& object, const std::string& name) {
    const auto& value = object.at(name);
    require(value.is_number_integer() &&
                (value.is_number_unsigned() || value.get<std::int64_t>() >= 0),
            "expected nonnegative integer: " + name);
    const auto number = value.get<std::uint64_t>();
    require(number <= safe_integer, "integer exceeds canonical safe range: " + name);
    return number;
}
void shape(const Json& object, const std::set<std::string>& required,
           const std::set<std::string>& optional = {}) {
    auto allowed = required;
    allowed.insert(optional.begin(), optional.end());
    aslice::core::take(fields(object, allowed));
    for (const auto& field : required) {
        require(object.contains(field), "missing manifest field: " + field);
    }
}
void pattern(const std::string& value, const char* expression, const std::string& label) {
    require(std::regex_match(value, std::regex(expression)), "invalid " + label);
}
void identity(const Json& object) {
    for (const auto* field : {"repository", "name"}) {
        pattern(string(object, field), "[a-z0-9][a-z0-9-]*", field);
    }
}
void array(const Json& value, std::size_t limit) {
    require(value.is_array() && value.size() <= limit, "invalid or oversized manifest array");
}
void unique_strings(const Json& value, const char* expression = nullptr) {
    array(value, metadata_list_limit);
    std::set<std::string> seen;
    for (const auto& entry : value) {
        const auto item = entry.get<std::string>();
        require(seen.insert(item).second, "duplicate manifest array value");
        if (expression) {
            pattern(item, expression, "manifest array value");
        }
    }
}
void path(const std::string& value) {
    // Conservative portable subset until Unicode normalization is implemented.
    require(!value.empty() && value.size() <= 1024 && value.front() != '/' && value.back() != '/' &&
                value.find_first_not_of(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+/") ==
                    value.npos,
            "manifest path is outside the supported portable ASCII subset");
    require(fs::path(value).lexically_normal().generic_string() == value,
            "unnormalized manifest path");
    for (const auto& component : fs::path(value)) {
        require(component != "." && component != "..", "unsafe manifest path");
    }
}
std::string folded(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return c >= 'A' && c <= 'Z' ? static_cast<char>(c + 32) : static_cast<char>(c);
    });
    return value;
}
// RFC 8785 object names sort as UTF-16 code units. JSON parsing already validates UTF-8.
std::u16string utf16(const std::string& value) {
    std::u16string out;
    for (std::size_t i = 0; i < value.size();) {
        auto cp = static_cast<unsigned char>(value[i++]);
        std::uint32_t code = cp;
        unsigned continuation = 0;
        if (cp >= 0xf0) {
            code &= 7;
            continuation = 3;
        } else if (cp >= 0xe0) {
            code &= 15;
            continuation = 2;
        } else if (cp >= 0xc0) {
            code &= 31;
            continuation = 1;
        }
        require(i + continuation <= value.size(), "invalid UTF-8 key");
        while (continuation--) {
            code = (code << 6) | (static_cast<unsigned char>(value[i++]) & 63);
        }
        if (code <= 0xffff) {
            out.push_back(static_cast<char16_t>(code));
        } else {
            code -= 0x10000;
            out.push_back(static_cast<char16_t>(0xd800 + (code >> 10)));
            out.push_back(static_cast<char16_t>(0xdc00 + (code & 1023)));
        }
    }
    return out;
}
std::string canonical(const Json& value) {
    if (value.is_object()) {
        std::vector<std::pair<std::u16string, std::string>> names;
        for (const auto& [name, unused] : value.items()) {
            (void)unused;
            names.emplace_back(utf16(name), name);
        }
        std::sort(names.begin(), names.end());
        std::string result = "{";
        for (const auto& [sort_key, name] : names) {
            (void)sort_key;
            if (result.size() != 1) {
                result += ',';
            }
            result += Json(name).dump() + ':' + canonical(value.at(name));
        }
        return result + '}';
    }
    if (value.is_array()) {
        std::string result = "[";
        for (const auto& item : value) {
            if (result.size() != 1) {
                result += ',';
            }
            result += canonical(item);
        }
        return result + ']';
    }
    require(!value.is_number_float(), "floating point is not a manifest field type");
    return value.dump();
}
void abi(const Json& value) {
    shape(value, {"provides", "requires"});
    for (const auto* category : {"provides", "requires"}) {
        array(value.at(category), metadata_list_limit);
        std::set<std::pair<std::string, std::string>> seen;
        const bool provides = std::string_view(category) == "provides";
        for (const auto& entry : value.at(category)) {
            if (provides) {
                shape(entry, {"install_name", "arch", "current_version", "compatibility_version",
                              "symbols", "evidence"});
            } else {
                shape(entry, {"install_name", "arch", "min_compat", "symbols"});
            }
            const auto name = string(entry, "install_name");
            const auto arch = string(entry, "arch");
            require(!name.empty() && (arch == "x86_64" || arch == "i386") &&
                        seen.emplace(name, arch).second,
                    "invalid or duplicate ABI record");
            unique_strings(entry.at("symbols"));
            if (provides) {
                pattern(string(entry, "current_version"), "[0-9]+\\.[0-9]+\\.[0-9]+",
                        "ABI version");
                pattern(string(entry, "compatibility_version"), "[0-9]+\\.[0-9]+\\.[0-9]+",
                        "ABI version");
                const auto evidence = string(entry, "evidence");
                require(evidence == "c-interface" || evidence == "validated-cxx" ||
                            evidence == "unknown",
                        "invalid ABI evidence");
            } else {
                pattern(string(entry, "min_compat"), "[0-9]+\\.[0-9]+\\.[0-9]+", "ABI version");
            }
        }
    }
}
std::string file_digest(platform::FileSystem& filesystem, const platform::TargetPath& file,
                        std::uint64_t size, const std::vector<Relocation>& relocations,
                        const std::string& name, unsigned expected_mode) {
    std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)> context(EVP_MD_CTX_new(),
                                                                    EVP_MD_CTX_free);
    require(context && EVP_DigestInit_ex(context.get(), EVP_sha256(), nullptr) == 1,
            "cannot initialize SHA-256");
    std::uint64_t count = 0;
    filesystem.stream(
        file, static_cast<std::size_t>(size),
        [&](std::string_view bytes) {
            require(EVP_DigestUpdate(context.get(), bytes.data(), bytes.size()) == 1,
                    "SHA-256 update failed");
            for (const auto& relocation : relocations) {
                if (relocation.path != name) {
                    continue;
                }
                const auto start = std::max<std::uint64_t>(count, relocation.offset);
                const auto end = std::min<std::uint64_t>(
                    count + bytes.size(), relocation.offset + relocation.expected_hex.size() / 2);
                for (auto offset = start; offset < end; ++offset) {
                    require(
                        static_cast<unsigned char>(
                            bytes[static_cast<std::size_t>(offset - count)]) ==
                            std::stoul(
                                relocation.expected_hex.substr(
                                    static_cast<std::size_t>(offset - relocation.offset) * 2, 2),
                                nullptr, 16),
                        "relocation expected bytes mismatch");
                }
            }
            count += bytes.size();
        },
        [&](const platform::NodeStatus& metadata) {
            require(metadata.kind == platform::NodeKind::file && metadata.links == 1,
                    "opened payload must be a regular file with one link");
            require(!filesystem.supports_posix_modes() || metadata.mode == expected_mode,
                    "opened payload mode mismatch: " + name);
        });
    require(count == size, "payload read failed or size changed");
    std::array<unsigned char, EVP_MAX_MD_SIZE> hash{};
    unsigned length = 0;
    require(EVP_DigestFinal_ex(context.get(), hash.data(), &length) == 1,
            "SHA-256 finalization failed");
    std::string result;
    for (unsigned i = 0; i < length; ++i) {
        result += "0123456789abcdef"[hash[i] >> 4];
        result += "0123456789abcdef"[hash[i] & 15];
    }
    return result;
}
void validate_header(const Json& document) {
    shape(document,
          {"manifest_version", "repository", "name", "version", "epoch", "revision", "build_id",
           "recipe_digest", "user_flags", "cpu_features", "requires_i386", "min_os", "files",
           "dependencies", "relocations", "abi"},
          {"max_os"});
    require(integer(document, "manifest_version") == 1, "unsupported manifest version");
    identity(document);
    aslice::core::take(Version::parse(string(document, "version")));
    require(string(document, "version").find('!') == std::string::npos,
            "manifest epoch belongs in its separate field");
    integer(document, "epoch");
    integer(document, "revision");
    pattern(string(document, "build_id"), "[0-9a-f]{64}", "build ID");
    pattern(string(document, "recipe_digest"), "sha256:[0-9a-f]{64}", "recipe digest");
    const auto minimum = core::take(os_rank(string(document, "min_os")));
    if (document.contains("max_os")) {
        require(core::take(os_rank(string(document, "max_os"))) >= minimum,
                "empty manifest OS range");
    }
    require(document.at("requires_i386").is_boolean(), "requires_i386 must be boolean");
    require(document.at("user_flags").is_object(), "user_flags must be an object");
    for (const auto& [name, flag] : document["user_flags"].items()) {
        (void)name;
        require(flag.is_string(), "user flag must be a string");
    }
    unique_strings(document.at("cpu_features"), "[a-z0-9_]+");
}
std::set<std::string> validate_dependencies(const Json& document) {
    array(document.at("dependencies"), metadata_list_limit);
    std::set<std::string> dependencies;
    for (const auto& dependency : document["dependencies"]) {
        shape(dependency, {"repository", "name", "artifact_id"});
        identity(dependency);
        const auto name = string(dependency, "repository") + ':' + string(dependency, "name");
        require(dependencies.insert(name).second &&
                    name != string(document, "repository") + ':' + string(document, "name"),
                "duplicate or self dependency");
        pattern(string(dependency, "artifact_id"), "sha256:[0-9a-f]{64}", "dependency artifact ID");
    }
    return dependencies;
}
std::map<std::string, Json> validate_inventory(const Json& document, std::uint64_t& payload_bytes) {
    array(document.at("files"), inventory_entry_limit);
    std::map<std::string, Json> files;
    std::map<std::string, std::string> aliases;
    for (const auto& file : document["files"]) {
        const auto name = string(file, "path");
        const auto kind = string(file, "kind");
        path(name);
        pattern(string(file, "mode"), "0[0-7]{3}", "file mode");
        require(files.emplace(name, file).second, "duplicate manifest path");
        for (auto part = fs::path(name); !part.empty(); part = part.parent_path()) {
            const auto spelling = part.generic_string();
            const auto [it, inserted] = aliases.emplace(folded(spelling), spelling);
            require(inserted || it->second == spelling, "case-folded manifest path collision");
        }
        if (kind == "file") {
            shape(file, {"path", "kind", "mode", "size", "sha256"});
            pattern(string(file, "sha256"), "[0-9a-f]{64}", "file SHA-256");
            const auto size = integer(file, "size");
            require(size <= payload_limit - payload_bytes,
                    "payload exceeds the 1 GiB local inspection limit");
            payload_bytes += size;
        } else if (kind == "directory") {
            shape(file, {"path", "kind", "mode"});
        } else {
            require(kind == "symlink", "unsupported inventory kind");
            shape(file, {"path", "kind", "mode", "target"});
            const auto target = string(file, "target");
            require(
                !target.empty() && target.front() != '/' &&
                    target.find_first_not_of(
                        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+/") ==
                        target.npos,
                "unsafe symlink target");
        }
    }
    for (const auto& [name, file] : files) {
        for (auto parent = fs::path(name).parent_path(); !parent.empty();
             parent = parent.parent_path()) {
            require(!files.contains(parent.generic_string()) ||
                        files.at(parent.generic_string()).at("kind") == "directory",
                    "inventory entry below a non-directory");
        }
        if (file.at("kind") != "symlink") {
            continue;
        }
        // Resolve components in traversal order: lexical normalization would
        // erase a symlink (or regular file) immediately before a parent step.
        std::deque<std::string> pending;
        auto prepend = [&](const std::string& target) {
            std::vector<std::string> parts;
            for (const auto& component : fs::path(target)) {
                parts.push_back(component.generic_string());
            }
            pending.insert(pending.begin(), parts.begin(), parts.end());
        };
        prepend(string(file, "target"));
        auto resolved = fs::path(name).parent_path();
        unsigned expansions = 0;
        while (!pending.empty()) {
            const auto component = pending.front();
            pending.pop_front();
            if (component.empty() || component == ".") {
                continue;
            }
            if (component == "..") {
                require(!resolved.empty(), "symlink escapes payload root");
                resolved = resolved.parent_path();
                continue;
            }
            const auto next = resolved / component;
            const auto spelling = next.generic_string();
            path(spelling);
            const auto found = files.find(spelling);
            if (found != files.end() && found->second.at("kind") == "symlink") {
                require(++expansions <= 32, "symlink cycle or expansion limit exceeded");
                prepend(string(found->second, "target"));
                continue;
            }
            if (found == files.end()) {
                const auto child = files.lower_bound(spelling + '/');
                require(child != files.end() && child->first.starts_with(spelling + '/'),
                        "dangling inventory symlink");
            } else {
                require(pending.empty() || found->second.at("kind") == "directory",
                        "symlink traverses a non-directory");
            }
            resolved = next;
        }
    }
    return files;
}
void validate_relocations(const Json& document, const std::map<std::string, Json>& files,
                          const std::set<std::string>& dependencies) {
    array(document.at("relocations"), inventory_entry_limit);
    std::map<std::string, std::vector<std::pair<std::uint64_t, std::uint64_t>>> ranges;
    for (const auto& relocation : document["relocations"]) {
        shape(relocation, {"path", "offset", "width", "expected_hex", "replacement"});
        const auto name = string(relocation, "path");
        require(files.contains(name) && files.at(name).at("kind") == "file",
                "relocation must name an inventory file");
        const auto offset = integer(relocation, "offset");
        const auto width = integer(relocation, "width");
        const auto size = integer(files.at(name), "size");
        require(width > 0 && offset <= size && width <= size - offset, "relocation outside file");
        const auto expected = string(relocation, "expected_hex");
        pattern(expected, "([0-9a-f]{2})+", "relocation expected bytes");
        require(expected.size() / 2 == width, "relocation width mismatch");
        const auto replacement = string(relocation, "replacement");
        require(replacement == "self" || (replacement.starts_with("dependency:") &&
                                          dependencies.contains(replacement.substr(11))),
                "unbound relocation dependency");
        ranges[name].emplace_back(offset, offset + width);
    }
    for (auto& [name, spans] : ranges) {
        (void)name;
        std::sort(spans.begin(), spans.end());
        for (std::size_t i = 1; i < spans.size(); ++i) {
            require(spans[i - 1].second <= spans[i].first, "overlapping relocations");
        }
    }
}
void canonical_sets(Json& document) {
    auto strings = [](Json& values) {
        std::sort(values.begin(), values.end(), [](const Json& left, const Json& right) {
            return utf16(left.get_ref<const std::string&>()) <
                   utf16(right.get_ref<const std::string&>());
        });
    };
    strings(document.at("cpu_features"));
    auto& files = document.at("files");
    std::sort(files.begin(), files.end(), [](const Json& left, const Json& right) {
        return string(left, "path") < string(right, "path");
    });
    auto& dependencies = document.at("dependencies");
    std::sort(dependencies.begin(), dependencies.end(), [](const Json& left, const Json& right) {
        return std::pair{string(left, "repository"), string(left, "name")} <
               std::pair{string(right, "repository"), string(right, "name")};
    });
    for (const auto* category : {"provides", "requires"}) {
        auto& records = document.at("abi").at(category);
        for (auto& record : records) {
            strings(record.at("symbols"));
        }
        std::sort(records.begin(), records.end(), [](const Json& left, const Json& right) {
            return std::pair{utf16(string(left, "install_name")), string(left, "arch")} <
                   std::pair{utf16(string(right, "install_name")), string(right, "arch")};
        });
    }
    auto& relocations = document.at("relocations");
    std::sort(relocations.begin(), relocations.end(), [](const Json& left, const Json& right) {
        return std::pair{string(left, "path"), integer(left, "offset")} <
               std::pair{string(right, "path"), integer(right, "offset")};
    });
}
} // namespace

core::Result<Manifest> Manifest::parse(core::Json value) {
    try {
        return Manifest(std::move(value));
    } catch (const std::exception& error) {
        return tl::unexpected(core::Failure{"invalid_manifest", error.what()});
    }
}
Manifest::Manifest(Json value) : document_(std::move(value)) {
    namespace fs = std::filesystem;
    using core::digest;
    using core::fields;
    using core::Json;
    using core::require;
    validate_header(document_);
    const auto dependencies = validate_dependencies(document_);
    const auto files = validate_inventory(document_, payload_bytes_);
    validate_relocations(document_, files, dependencies);
    abi(document_.at("abi"));
    canonical_sets(document_);
    for (const auto& file : document_.at("files")) {
        inventory_.push_back(
            {file.at("path"), file.at("kind"),
             static_cast<unsigned>(std::stoul(file.at("mode").get<std::string>(), nullptr, 8)),
             file.value("size", std::uint64_t{0}), file.value("sha256", std::string{}),
             file.value("target", std::string{})});
    }
    for (const auto& relocation : document_.at("relocations")) {
        relocations_.push_back(
            {relocation.at("path"), relocation.at("offset"), relocation.at("expected_hex")});
    }
    canonical_ = package::canonical(document_);
    artifact_id_ = "sha256:" + aslice::core::take(digest(canonical_));
}

core::Json Manifest::inspect() const {
    return {{"artifact_id", artifact_id_},     {"manifest_size", canonical_.size()},
            {"payload_bytes", payload_bytes_}, {"payload_entries", document_.at("files").size()},
            {"authenticated", false},          {"manifest", document_}};
}

core::Json Manifest::verify_payload_impl(platform::FileSystem& filesystem,
                                         const platform::TargetPath& root) const {
    namespace fs = std::filesystem;
    using core::digest;
    using core::fields;
    using core::Json;
    using core::require;
    filesystem.no_symlinks(root);
    require(filesystem.status(root).kind == platform::NodeKind::directory,
            "payload root must be a directory");
    std::set<std::string> entries;
    for (const auto& file : document_.at("files")) {
        const auto name = string(file, "path");
        const auto kind = string(file, "kind");
        const auto full = root / name;
        filesystem.no_symlinks(full.parent_path());
        const auto status = filesystem.status(full);
        if (kind == "file") {
            require(status.kind == platform::NodeKind::file,
                    "payload is not a regular file: " + name);
            require(status.links == 1, "hard-linked payload file refused");
            require(file_digest(filesystem, full, integer(file, "size"), relocations_, name,
                                static_cast<unsigned>(std::stoul(string(file, "mode"), nullptr,
                                                                 8))) == string(file, "sha256"),
                    "payload digest mismatch: " + name);
        } else if (kind == "directory") {
            require(status.kind == platform::NodeKind::directory,
                    "missing payload directory: " + name);
        } else {
            require(status.kind == platform::NodeKind::symlink &&
                        filesystem.read_symlink(full) == string(file, "target"),
                    "payload symlink mismatch: " + name);
        }
        if (kind != "symlink" && filesystem.supports_posix_modes()) {
            require((status.mode & 07777) == std::stoul(string(file, "mode"), nullptr, 8),
                    "payload mode mismatch: " + name);
        }
        entries.insert(name);
        for (auto parent = fs::path(name).parent_path(); !parent.empty();
             parent = parent.parent_path()) {
            entries.insert(parent.generic_string());
        }
    }
    for (const auto& entry : filesystem.walk(root)) {
        require(entries.contains(entry.relative_to(root)), "unlisted payload entry");
    }
    auto result = inspect();
    result["payload_verified"] = true;
    result["posix_modes_verified"] = filesystem.supports_posix_modes();
    return result;
}

core::Result<core::Json> Manifest::verify_payload(platform::FileSystem& filesystem,
                                                  const platform::TargetPath& input) const {
    return core::capture([&] {
        return Manifest::verify_payload_impl(filesystem, input);
    });
}
} // namespace aslice::package
