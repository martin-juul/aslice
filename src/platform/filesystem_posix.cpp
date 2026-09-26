#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include <cerrno>
#include <cstddef>
#include <fcntl.h>
#include <filesystem>
#include <memory>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>
namespace aslice::platform {
namespace fs = std::filesystem;
using core::Error;
using core::require;
struct Fd {
    int value;
    explicit Fd(int number) : value(number) {
        if (value < 0) {
            throw Error("filesystem operation failed", "io");
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
void sync_directory_impl(const fs::path& path) {
    Fd fd(open(path.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (fsync(fd.value) != 0) {
        throw Error("directory sync failed: " + path.string(), "io");
    }
}
void write_new_impl(const fs::path& path, const std::string& bytes, unsigned mode) {
    Fd fd(open(path.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, mode));
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
    Fd fd;
    explicit Impl(const fs::path& root)
        : fd(open((root / ".lock").c_str(), O_RDWR | O_CLOEXEC | O_NOFOLLOW)) {
        if (flock(fd.value, LOCK_EX | LOCK_NB) != 0) {
            throw Error("prototype prefix is busy; retry after its owner finishes", "busy");
        }
    }
};
void private_umask_impl() {
    umask(0077);
}
void check_private_directory_impl(const fs::path& root) {
    struct stat info{};
    require(lstat(root.c_str(), &info) == 0 && S_ISDIR(info.st_mode) && info.st_uid == geteuid() &&
                (info.st_mode & 077) == 0,
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
