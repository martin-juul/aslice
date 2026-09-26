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
#include <algorithm>
#include <cstddef>
#include <fileapi.h>
#include <filesystem>
#include <handleapi.h>
#include <memory>
#include <minwindef.h>
#include <string>
#include <utility>
#include <winnt.h>
namespace aslice::platform {
namespace {
[[noreturn]] void unsupported() {
    throw core::Error("Use Docker or WSL for POSIX prefix operations");
}
} // namespace
void sync_directory_impl(const core::fs::path&) {
    unsupported();
}
void write_new_impl(const core::fs::path& path, const std::string& bytes, unsigned) {
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
    } handle{CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL,
                         nullptr)};
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
