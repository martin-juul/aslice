#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <dirent.h>
#include <fcntl.h>
#include <filesystem>
#include <memory>
#include <stdio.h>
#include <string>
#include <string_view>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <utility>
#include <vector>
namespace aslice::platform {
namespace fs = std::filesystem;
using core::Error;
using core::require;
struct Fd {
    int value;
    explicit Fd(int number) : value(number) {
        if (value < 0) {
            throw Error("filesystem operation failed", errno == ENOENT ? "not-found"
                                                       : errno == ELOOP || errno == ENOTDIR
                                                           ? "invalid"
                                                           : "io");
        }
    }
    ~Fd() {
        if (value >= 0) {
            close(value);
        }
    }
    Fd(Fd&& other) noexcept : value(std::exchange(other.value, -1)) {}
    Fd& operator=(Fd&& other) noexcept {
        if (this != &other) {
            if (value >= 0) {
                close(value);
            }
            value = std::exchange(other.value, -1);
        }
        return *this;
    }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
};
namespace {
Fd open_directory(const fs::path& path) {
    require(path.is_absolute(), "native directory path must be absolute");
    Fd directory(open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC));
    for (const auto& component : path.relative_path()) {
        require(component != ".." && component != ".", "noncanonical native directory path");
        directory = Fd(openat(directory.value, component.c_str(),
                              O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    }
    return directory;
}
Fd open_parent(const fs::path& path) {
    return open_directory(path.parent_path());
}
NodeStatus metadata(const struct stat& info) {
    return {S_ISREG(info.st_mode)   ? NodeKind::file
            : S_ISDIR(info.st_mode) ? NodeKind::directory
            : S_ISLNK(info.st_mode) ? NodeKind::symlink
                                    : NodeKind::other,
            static_cast<unsigned>(info.st_mode & 07777), static_cast<std::uint64_t>(info.st_nlink)};
}
void checked_mutation(int result, const char* operation) {
    if (result != 0) {
        throw Error(std::string(operation) + " failed", "io");
    }
}
} // namespace
NodeStatus NativeFileSystem::status(const TargetPath& path) {
    try {
        struct stat info{};
        if (path.string() == "/") {
            const auto root = open_directory("/");
            checked_mutation(fstat(root.value, &info), "stat root");
        } else {
            const auto parent = open_parent(path.string());
            if (fstatat(parent.value, path.filename().c_str(), &info, AT_SYMLINK_NOFOLLOW) != 0) {
                if (errno == ENOENT) {
                    return {};
                }
                throw Error("cannot stat target", "io");
            }
        }
        return metadata(info);
    } catch (const Error& error) {
        if (error.code == "not-found") {
            return {};
        }
        throw;
    }
}
std::vector<TargetPath> NativeFileSystem::list(const TargetPath& path) {
    auto directory = open_directory(path.string());
    struct CloseDirectory {
        void operator()(DIR* value) const {
            closedir(value);
        }
    };
    std::unique_ptr<DIR, CloseDirectory> entries(fdopendir(directory.value));
    require(entries != nullptr, "cannot enumerate directory");
    directory.value = -1; // fdopendir now owns this descriptor.
    std::vector<TargetPath> result;
    for (;;) {
        errno = 0;
        const auto* entry = readdir(entries.get());
        if (!entry) {
            checked_mutation(errno, "read directory");
            break;
        }
        const std::string name{entry->d_name};
        if (name != "." && name != "..") {
            require(result.size() < 100000, "directory listing exceeds fixture limit");
            result.push_back(path / name);
        }
    }
    std::sort(result.begin(), result.end(), [](const auto& a, const auto& b) {
        return a.string() < b.string();
    });
    return result;
}
void NativeFileSystem::mkdir(const TargetPath& path) {
    const auto parent = open_parent(path.string());
    checked_mutation(mkdirat(parent.value, path.filename().c_str(), 0777), "mkdir");
}
void NativeFileSystem::permissions(const TargetPath& path, unsigned mode) {
    const auto parent = open_parent(path.string());
    const Fd file(openat(parent.value, path.filename().c_str(),
                         O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK));
    struct stat info{};
    require(fstat(file.value, &info) == 0 && (S_ISREG(info.st_mode) || S_ISDIR(info.st_mode)),
            "mode change requires a regular file or directory");
    checked_mutation(fchmod(file.value, static_cast<mode_t>(mode)), "chmod");
}
void NativeFileSystem::create_symlink(const std::string& target, const TargetPath& path) {
    require(target.find('\0') == std::string::npos, "invalid symlink target");
    const auto parent = open_parent(path.string());
    checked_mutation(symlinkat(target.c_str(), parent.value, path.filename().c_str()), "symlink");
}
std::string NativeFileSystem::read_symlink(const TargetPath& path) {
    const auto parent = open_parent(path.string());
    std::array<char, 65536> buffer{};
    const auto size =
        readlinkat(parent.value, path.filename().c_str(), buffer.data(), buffer.size());
    require(size >= 0 && static_cast<std::size_t>(size) < buffer.size(),
            "cannot read link or link exceeds limit");
    return {buffer.data(), static_cast<std::size_t>(size)};
}
void NativeFileSystem::rename(const TargetPath& source, const TargetPath& destination) {
    const auto from = open_parent(source.string());
    const auto to = open_parent(destination.string());
    checked_mutation(
        renameat(from.value, source.filename().c_str(), to.value, destination.filename().c_str()),
        "rename");
}
void NativeFileSystem::remove(const TargetPath& path) {
    const auto parent = open_parent(path.string());
    struct stat info{};
    checked_mutation(fstatat(parent.value, path.filename().c_str(), &info, AT_SYMLINK_NOFOLLOW),
                     "stat for remove");
    checked_mutation(
        unlinkat(parent.value, path.filename().c_str(), S_ISDIR(info.st_mode) ? AT_REMOVEDIR : 0),
        "remove");
}
void NativeFileSystem::stream(const TargetPath& path, std::size_t maximum, const Consumer& consume,
                              const Inspector& inspect) {
    // Pin each directory before traversing the next component. No pathname
    // preflight can substitute for O_NOFOLLOW on the actual open operation.
    const auto parent = open_parent(path.string());
    // NONBLOCK avoids hanging on a substituted FIFO before fstat rejects it.
    Fd file(openat(parent.value, path.filename().c_str(),
                   O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK));
    struct stat info{};
    require(fstat(file.value, &info) == 0 && S_ISREG(info.st_mode) && info.st_size >= 0,
            "expected an opened regular file");
    require(static_cast<std::uint64_t>(info.st_size) <= maximum,
            "file exceeds prototype size limit");
    if (inspect) {
        inspect({NodeKind::file, static_cast<unsigned>(info.st_mode & 07777),
                 static_cast<std::uint64_t>(info.st_nlink)});
    }
    std::array<char, 65536> buffer{};
    std::size_t total = 0;
    for (;;) {
        const auto count = ::read(file.value, buffer.data(), buffer.size());
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            throw Error("file read failed", "io");
        }
        if (count == 0) {
            return;
        }
        const auto size = static_cast<std::size_t>(count);
        require(size <= maximum - total, "file grew beyond size limit");
        total += size;
        consume(std::string_view{buffer.data(), size});
    }
}
void sync_directory_impl(const fs::path& path) {
    const auto fd = open_directory(path);
    if (fsync(fd.value) != 0) {
        throw Error("directory sync failed: " + path.string(), "io");
    }
}
void write_new_impl(const fs::path& path, const std::string& bytes, unsigned mode) {
    const auto parent = open_parent(path);
    Fd fd(openat(parent.value, path.filename().c_str(),
                 O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode));
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        const auto written = write(fd.value, bytes.data() + offset, bytes.size() - offset);
        if (written < 0 && errno == EINTR) {
            continue;
        }
        if (written <= 0) {
            throw Error("write failed: " + path.string(), "io");
        }
        offset += static_cast<std::size_t>(written);
    }
    if (fsync(fd.value) != 0) {
        throw Error("file sync failed: " + path.string(), "io");
    }
}

struct Lock::Impl {
    static Fd open_lock(const fs::path& root) {
        const auto parent = open_directory(root);
        Fd file(openat(parent.value, ".lock", O_RDWR | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK));
        struct stat info{};
        require(fstat(file.value, &info) == 0 && S_ISREG(info.st_mode) && info.st_nlink == 1 &&
                    info.st_uid == geteuid(),
                "lock must be a regular single-link file owned by the current user");
        return file;
    }
    Fd fd;
    explicit Impl(const fs::path& root) : fd(open_lock(root)) {
        if (flock(fd.value, LOCK_EX | LOCK_NB) != 0) {
            throw Error("prototype prefix is busy; retry after its owner finishes", "busy");
        }
    }
};
void private_umask_impl() {
    umask(0077);
}
void check_private_directory_impl(const fs::path& root) {
    const auto directory = open_directory(root);
    struct stat info{};
    require(fstat(directory.value, &info) == 0 && S_ISDIR(info.st_mode) &&
                info.st_uid == geteuid() && (info.st_mode & 077) == 0,
            "prefix must be a private directory owned by the current user");
}

Lock::Lock(std::unique_ptr<Impl> implementation) : implementation_(std::move(implementation)) {}
Lock::~Lock() = default;
Lock::Lock(Lock&&) noexcept = default;
Lock& Lock::operator=(Lock&&) noexcept = default;
core::Result<Lock> Lock::acquire(const core::fs::path& root) {
    return core::capture([&] {
        return Lock(std::make_unique<Impl>(root));
    });
}

core::Result<void> sync_directory(const core::fs::path& path) {
    return core::capture([&] {
        sync_directory_impl(path);
    });
}

core::Result<void> write_new(const core::fs::path& path, const std::string& bytes, unsigned mode) {
    return core::capture([&] {
        write_new_impl(path, bytes, mode);
    });
}

core::Result<void> private_umask() {
    return core::capture([&] {
        private_umask_impl();
    });
}

core::Result<void> check_private_directory(const core::fs::path& path) {
    return core::capture([&] {
        check_private_directory_impl(path);
    });
}
} // namespace aslice::platform
