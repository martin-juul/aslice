#include "platform/target_filesystem_simulator.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/simulator.hpp"
#include "platform/target_filesystem.hpp"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <memory>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace aslice::platform {
namespace {
core::Json checked(const core::Json& response) {
    if (!response.at("failure").is_null()) {
        const auto& failure = response.at("failure");
        auto code = failure.at("code").get<std::string>();
        if (code == "injected" || code == "no-space") {
            code = "io";
        }
        throw core::Error(failure.at("message").get<std::string>(), code);
    }
    return response.at("result");
}
std::string encode(std::string_view bytes) {
    constexpr std::string_view digits = "0123456789abcdef";
    std::string result;
    result.reserve(bytes.size() * 2);
    for (const auto byte : bytes) {
        const auto value = static_cast<unsigned char>(byte);
        result += digits[value >> 4];
        result += digits[value & 15];
    }
    return result;
}
std::string decode(const std::string& hex) {
    core::require(hex.size() % 2 == 0, "invalid platform bytes");
    auto digit = [](char value) -> unsigned {
        if (value >= '0' && value <= '9') {
            return static_cast<unsigned>(value - '0');
        }
        if (value >= 'a' && value <= 'f') {
            return static_cast<unsigned>(value - 'a' + 10);
        }
        throw core::Error("invalid platform hex byte");
    };
    std::string result;
    result.reserve(hex.size() / 2);
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        result += static_cast<char>((digit(hex[i]) << 4) | digit(hex[i + 1]));
    }
    return result;
}
class RemoteLock final : public FileLock {
  public:
    RemoteLock(Simulator& connection, TargetPath path)
        : connection_(connection), path_(std::move(path)) {
        checked(core::take(connection_.filesystem("lock", path_)));
    }
    ~RemoteLock() override {
        // Process exit releases retained OS locks, including an unknown unlock outcome.
        try {
            (void)connection_.filesystem("unlock", path_);
        } catch (const std::exception&) {
        }
    }

  private:
    Simulator& connection_;
    TargetPath path_;
};
class RemoteFile {
  public:
    RemoteFile(Simulator& connection, core::Json handle)
        : connection_(connection), handle_(std::move(handle)) {}
    ~RemoteFile() {
        try {
            (void)connection_.request("filesystem", "close", {{"handle", handle_}});
        } catch (const std::exception&) {
        }
    }
    RemoteFile(const RemoteFile&) = delete;
    RemoteFile& operator=(const RemoteFile&) = delete;

  private:
    Simulator& connection_;
    core::Json handle_;
};
} // namespace
core::Json SimulatorFileSystem::operation(const std::string& name, const TargetPath& path,
                                          const core::Json& arguments) {
    return checked(core::take(connection_.filesystem(name, path, arguments)));
}
bool SimulatorFileSystem::supports_prefix_operations() const {
    return true;
}
TargetPath SimulatorFileSystem::absolute(const std::string& path) const {
    return TargetPath{path};
}
NodeStatus SimulatorFileSystem::status(const TargetPath& path) {
    const auto response = core::take(connection_.filesystem("stat", path));
    if (!response.at("failure").is_null() && response.at("failure").at("code") == "not-found") {
        return {};
    }
    const auto node = checked(response);
    const auto kind = node.at("kind").get<std::string>();
    return {kind == "file"        ? NodeKind::file
            : kind == "directory" ? NodeKind::directory
            : kind == "symlink"   ? NodeKind::symlink
                                  : NodeKind::other,
            node.at("mode").get<unsigned>(), node.at("links").get<std::uint64_t>()};
}
std::vector<TargetPath> SimulatorFileSystem::list(const TargetPath& path) {
    std::vector<TargetPath> result;
    for (const auto& name : operation("list", path)) {
        result.push_back(path / name.get<std::string>());
    }
    std::sort(result.begin(), result.end(), [](const auto& left, const auto& right) {
        return left.string() < right.string();
    });
    return result;
}
bool SimulatorFileSystem::supports_posix_modes() const {
    return true;
}
void SimulatorFileSystem::stream(const TargetPath& path, std::size_t maximum,
                                 const Consumer& consume, const Inspector& inspect) {
    const auto node = operation("open_read", path);
    const auto& handle = node.at("handle");
    const RemoteFile file{connection_, handle};
    if (inspect) {
        inspect({NodeKind::file, node.at("mode").get<unsigned>(),
                 node.at("links").get<std::uint64_t>()});
    }
    core::require(node.at("size").get<std::size_t>() <= maximum,
                  "file exceeds prototype size limit");
    std::size_t total = 0;
    for (;;) {
        const auto bytes =
            decode(checked(core::take(connection_.request(
                               "filesystem", "read_handle",
                               {{"handle", handle}, {"offset", total}, {"length", 65536}})))
                       .at("hex"));
        core::require(bytes.size() <= maximum - total, "file grew beyond size limit");
        total += bytes.size();
        if (!bytes.empty()) {
            consume(bytes);
        }
        if (bytes.empty()) {
            return;
        }
    }
}
void SimulatorFileSystem::mkdir(const TargetPath& path) {
    operation("mkdir", path, {{"mode", 0777}});
}
void SimulatorFileSystem::permissions(const TargetPath& path, unsigned mode) {
    operation("chmod", path, {{"mode", mode}});
}
void SimulatorFileSystem::create_symlink(const std::string& target, const TargetPath& path) {
    operation("symlink", path, {{"target", target}});
}
std::string SimulatorFileSystem::read_symlink(const TargetPath& path) {
    return operation("readlink", path).at("target").get<std::string>();
}
void SimulatorFileSystem::rename(const TargetPath& source, const TargetPath& destination) {
    operation("rename", source, {{"destination", destination.string()}});
}
void SimulatorFileSystem::remove(const TargetPath& path) {
    operation("unlink", path);
}
void SimulatorFileSystem::write_new(const TargetPath& path, const std::string& bytes,
                                    unsigned mode) {
    const auto handle = operation("open_new", path, {{"mode", mode}}).at("handle");
    const RemoteFile file{connection_, handle};
    for (std::size_t offset = 0; offset < bytes.size();) {
        const auto count = std::min<std::size_t>(65536, bytes.size() - offset);
        const auto result = checked(core::take(
            connection_.request("filesystem", "write_handle",
                                {{"handle", handle},
                                 {"offset", offset},
                                 {"hex", encode(std::string_view{bytes}.substr(offset, count))}})));
        const auto written = result.at("written").get<std::size_t>();
        core::require(written > 0 && written <= count, "invalid platform write count");
        offset += written;
    }
    checked(core::take(connection_.request("filesystem", "flush_handle", {{"handle", handle}})));
}
void SimulatorFileSystem::sync_directory(const TargetPath& path) {
    operation("flush_directory", path);
}
void SimulatorFileSystem::private_umask() {
    checked(core::take(connection_.request("process", "umask", {{"mask", 0077}})));
}
void SimulatorFileSystem::check_private_directory(const TargetPath& path) {
    const auto process = checked(core::take(connection_.request("process", "observe")));
    const auto node = operation("stat", path);
    core::require(node.at("kind") == "directory" && node.at("uid") == process.at("uid") &&
                      (node.at("mode").get<unsigned>() & 07077U) == 0 && node.at("acl").empty() &&
                      node.value("flags", 0U) == 0,
                  "prefix must be a private directory owned by the current user");
}
std::unique_ptr<FileLock> SimulatorFileSystem::lock(const TargetPath& root) {
    return std::make_unique<RemoteLock>(connection_, root / ".lock");
}
void SimulatorFileSystem::checkpoint(const std::string& name) {
    checked(core::take(connection_.request("process", "checkpoint", {{"name", name}})));
}
} // namespace aslice::platform
