#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <string>
#include <utility>

#ifdef _WIN32
#include <algorithm>
#include <system_error>
#include <vector>
#endif

namespace aslice::platform {
namespace {
HostPath host_path(const TargetPath& path) {
#ifdef _WIN32
    const auto& value = path.string();
    core::require(value.size() >= 3 && value[0] == '/' && value[2] == ':' &&
                      (value.size() == 3 || value[3] == '/'),
                  "native Windows target must name a drive");
    return HostPath{
        std::filesystem::path{value.size() == 3 ? value.substr(1) + "/" : value.substr(1)}};
#else
    return HostPath{std::filesystem::path{path.string()}};
#endif
}
class NativeLock final : public FileLock {
  public:
    explicit NativeLock(Lock lock) : lock_(std::move(lock)) {}

  private:
    Lock lock_;
};
} // namespace
bool NativeFileSystem::supports_prefix_operations() const {
#ifdef _WIN32
    return false;
#else
    return true;
#endif
}
TargetPath NativeFileSystem::absolute(const std::string& path) const {
    auto value = std::filesystem::absolute(path).lexically_normal().generic_string();
#ifdef _WIN32
    core::require(value.size() >= 3 && value[1] == ':' && value[2] == '/',
                  "native Windows inspection requires a drive path");
    value = '/' + value;
    if (value.back() == '/') {
        value.pop_back();
    }
#endif
    return TargetPath{value};
}
#ifdef _WIN32
NodeStatus NativeFileSystem::status(const TargetPath& path) {
    std::error_code error;
    const auto value = std::filesystem::symlink_status(host_path(path).path(), error);
    if (error == std::errc::no_such_file_or_directory) {
        return {};
    }
    if (error) {
        throw core::Error("cannot stat target: " + error.message(), "io");
    }
    NodeKind kind = NodeKind::other;
    if (!std::filesystem::exists(value)) {
        kind = NodeKind::missing;
    } else if (std::filesystem::is_symlink(value)) {
        kind = NodeKind::symlink;
    } else if (std::filesystem::is_directory(value)) {
        kind = NodeKind::directory;
    } else if (std::filesystem::is_regular_file(value)) {
        kind = NodeKind::file;
    }
    const auto links =
        kind == NodeKind::file ? std::filesystem::hard_link_count(host_path(path).path()) : 0;
    return {kind, static_cast<unsigned>(value.permissions() & std::filesystem::perms::all), links};
}
#endif
std::string NativeFileSystem::display_path(const TargetPath& path) const {
    return host_path(path).path().string();
}
#ifdef _WIN32
std::vector<TargetPath> NativeFileSystem::list(const TargetPath& path) {
    std::vector<TargetPath> result;
    for (const auto& entry : std::filesystem::directory_iterator(host_path(path).path())) {
        result.push_back(path / entry.path().filename().generic_string());
    }
    std::sort(result.begin(), result.end(), [](const auto& left, const auto& right) {
        return left.string() < right.string();
    });
    return result;
}
#endif
bool NativeFileSystem::supports_posix_modes() const {
#ifdef _WIN32
    return false;
#else
    return true;
#endif
}
#ifdef _WIN32
void NativeFileSystem::mkdir(const TargetPath& path) {
    core::require(std::filesystem::create_directory(host_path(path).path()),
                  "directory already exists");
}
void NativeFileSystem::permissions(const TargetPath& path, unsigned mode) {
    std::filesystem::permissions(host_path(path).path(), static_cast<std::filesystem::perms>(mode));
}
void NativeFileSystem::create_symlink(const std::string& target, const TargetPath& path) {
    std::filesystem::create_symlink(target, host_path(path).path());
}
std::string NativeFileSystem::read_symlink(const TargetPath& path) {
    return std::filesystem::read_symlink(host_path(path).path()).generic_string();
}
void NativeFileSystem::rename(const TargetPath& source, const TargetPath& destination) {
    std::filesystem::rename(host_path(source).path(), host_path(destination).path());
}
void NativeFileSystem::remove(const TargetPath& path) {
    core::require(std::filesystem::remove(host_path(path).path()),
                  "target disappeared before removal");
}
#endif
void NativeFileSystem::write_new(const TargetPath& path, const std::string& bytes, unsigned mode) {
    core::take(platform::write_new(host_path(path).path(), bytes, mode));
}
void NativeFileSystem::sync_directory(const TargetPath& path) {
    core::take(platform::sync_directory(host_path(path).path()));
}
void NativeFileSystem::private_umask() {
    core::take(platform::private_umask());
}
void NativeFileSystem::check_private_directory(const TargetPath& path) {
    core::take(platform::check_private_directory(host_path(path).path()));
}
std::unique_ptr<FileLock> NativeFileSystem::lock(const TargetPath& root) {
    return std::make_unique<NativeLock>(core::take(Lock::acquire(host_path(root).path())));
}
void NativeFileSystem::checkpoint(const std::string& name) {
    const char* point = std::getenv("ASLICE_PROTOTYPE_FAILPOINT");
    if (point && name == point) {
        throw core::Error("injected fixture interruption: " + name, "io");
    }
}
} // namespace aslice::platform
