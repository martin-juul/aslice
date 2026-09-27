#include "core/support.hpp"
#include "core/result.hpp"
#include <array>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <ios>
#include <openssl/evp.h>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::core {
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw Error(message);
    }
}
std::string digest_impl(const std::string& bytes) {
    std::array<unsigned char, EVP_MAX_MD_SIZE> hash{};
    unsigned size = 0;
    require(EVP_Digest(bytes.data(), bytes.size(), hash.data(), &size, EVP_sha256(), nullptr) == 1,
            "SHA-256 failed");
    std::string out;
    constexpr std::string_view hex = "0123456789abcdef";
    for (unsigned i = 0; i < size; ++i) {
        out += hex[hash[i] >> 4];
        out += hex[hash[i] & 15];
    }
    return out;
}
void fields_impl(const Json& object, const std::set<std::string>& allowed) {
    require(object.is_object(), "expected a JSON object");
    for (const auto& [name, unused] : object.items()) {
        (void)unused;
        require(allowed.contains(name), "unsupported field: " + name);
    }
}
std::string read_bytes_impl(const fs::path& path, std::size_t maximum) {
    require(fs::is_regular_file(fs::symlink_status(path)),
            "expected a regular file: " + path.string());
    require(fs::file_size(path) <= maximum, "file exceeds prototype size limit");
    std::ifstream input(path, std::ios::binary);
    require(input.good(), "cannot read: " + path.string());
    std::string result;
    std::array<char, 65536> buffer{};
    while (input) {
        input.read(buffer.data(), buffer.size());
        const auto count = static_cast<std::size_t>(input.gcount());
        require(count <= maximum - result.size(), "file grew beyond size limit");
        result.append(buffer.data(), count);
    }
    require(!input.bad() && result.size() <= maximum, "file read failed or grew beyond limit");
    return result;
}
Json read_json_impl(const fs::path& path) {
    return aslice::core::take(parse_json(aslice::core::take(read_bytes(path))));
}
Json parse_json_impl(const std::string& bytes) {
    std::vector<std::set<std::string>> objects;
    return Json::parse(bytes, [&](int depth, Json::parse_event_t event, Json& item) {
        require(depth <= 64, "JSON nesting exceeds inspection limit");
        if (event == Json::parse_event_t::object_start) {
            objects.emplace_back();
        }
        if (event == Json::parse_event_t::key) {
            require(objects.back().insert(item.get<std::string>()).second, "duplicate JSON key");
        }
        if (event == Json::parse_event_t::object_end) {
            objects.pop_back();
        }
        return true;
    });
}
void no_symlinks_impl(const fs::path& path) {
    fs::path walked;
    for (const auto& part : path) {
        walked /= part;
        require(!fs::is_symlink(fs::symlink_status(walked)),
                "symlinked prototype path refused: " + walked.string());
    }
}

core::Result<std::string> digest(const std::string& bytes) {
    return core::capture([&] {
        return digest_impl(bytes);
    });
}

core::Result<std::string> read_bytes(const fs::path& path, std::size_t maximum) {
    return core::capture([&] {
        return read_bytes_impl(path, maximum);
    });
}

core::Result<Json> read_json(const fs::path& path) {
    return core::capture([&] {
        return read_json_impl(path);
    });
}

core::Result<Json> parse_json(const std::string& bytes) {
    return core::capture([&] {
        return parse_json_impl(bytes);
    });
}

core::Result<void> no_symlinks(const fs::path& path) {
    return core::capture([&] {
        return no_symlinks_impl(path);
    });
}

core::Result<void> fields(const Json& object, const std::set<std::string>& allowed) {
    return core::capture([&] {
        return fields_impl(object, allowed);
    });
}
} // namespace aslice::core
