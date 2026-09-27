#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
// Windows SDK leaf headers require umbrella definitions first.
// NOLINTNEXTLINE(misc-include-cleaner)
#include <windows.h>

#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <fileapi.h>
#include <filesystem>
#include <handleapi.h>
#include <memory>
#include <minwindef.h>
#include <string>
#include <string_view>
#include <utility>
#include <winnt.h>
namespace aslice::platform {
namespace {
struct Handle {
    HANDLE value;
    explicit Handle(HANDLE raw) : value(raw) {}
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    Handle(Handle&& other) noexcept : value(std::exchange(other.value, INVALID_HANDLE_VALUE)) {}
    Handle& operator=(Handle&& other) noexcept {
        if (this != &other) {
            if (value != INVALID_HANDLE_VALUE) {
                CloseHandle(value);
            }
            value = std::exchange(other.value, INVALID_HANDLE_VALUE);
        }
        return *this;
    }
    ~Handle() {
        if (value != INVALID_HANDLE_VALUE) {
            CloseHandle(value);
        }
    }
};
[[noreturn]] void unsupported() {
    throw core::Error("Use Docker or WSL for POSIX prefix operations");
}
} // namespace
void sync_directory_impl(const core::fs::path&) {
    unsupported();
}
void NativeFileSystem::stream(const TargetPath& path, std::size_t maximum, const Consumer& consume,
                              const Inspector& inspect) {
    const std::filesystem::path file{display_path(path)};
    for (auto parent = file.parent_path(); !parent.empty(); parent = parent.parent_path()) {
        const auto attributes = GetFileAttributesW(parent.c_str());
        core::require(attributes != INVALID_FILE_ATTRIBUTES &&
                          (attributes & FILE_ATTRIBUTE_REPARSE_POINT) == 0,
                      "missing or reparse-point input parent refused");
        if (parent == parent.root_path()) {
            break;
        }
    }
    Handle handle{CreateFileW(file.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                              FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN, nullptr)};
    core::require(handle.value != INVALID_HANDLE_VALUE, "cannot open input file");
    BY_HANDLE_FILE_INFORMATION info{};
    core::require(GetFileType(handle.value) == FILE_TYPE_DISK &&
                      GetFileInformationByHandle(handle.value, &info) &&
                      (info.dwFileAttributes &
                       (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) == 0,
                  "expected an opened regular file");
    const auto size = (static_cast<std::uint64_t>(info.nFileSizeHigh) << 32) | info.nFileSizeLow;
    core::require(size <= maximum, "file exceeds prototype size limit");
    if (inspect) {
        inspect({NodeKind::file, 0, info.nNumberOfLinks});
    }
    std::array<char, 65536> buffer{};
    std::size_t total = 0;
    for (;;) {
        DWORD count = 0;
        if (!ReadFile(handle.value, buffer.data(), static_cast<DWORD>(buffer.size()), &count,
                      nullptr)) {
            throw core::Error("file read failed", "io");
        }
        if (count == 0) {
            return;
        }
        core::require(count <= maximum - total, "file grew beyond size limit");
        total += count;
        consume(std::string_view{buffer.data(), count});
    }
}
void write_new_impl(const core::fs::path& path, const std::string& bytes, unsigned) {
    Handle handle{CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                              FILE_ATTRIBUTE_NORMAL, nullptr)};
    core::require(handle.value != INVALID_HANDLE_VALUE,
                  "cannot create output; existing files are never replaced");
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        DWORD written = 0;
        const auto count = static_cast<DWORD>(std::min<std::size_t>(bytes.size() - offset, 65536));
        core::require(WriteFile(handle.value, bytes.data() + offset, count, &written, nullptr) &&
                          written > 0,
                      "cannot write output");
        offset += written;
    }
    core::require(FlushFileBuffers(handle.value), "cannot flush output");
}
void private_umask_impl() {
    unsupported();
}
void check_private_directory_impl(const core::fs::path&) {
    unsupported();
}
struct Lock::Impl {
    explicit Impl(const core::fs::path&) {
        unsupported();
    }
};

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
