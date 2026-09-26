#ifndef ASLICE_PLATFORM_FILESYSTEM_HPP
#define ASLICE_PLATFORM_FILESYSTEM_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include <filesystem>
#include <memory>
#include <string>

namespace aslice::platform {
// Prefix operations require POSIX; exclusive file output is supported on Windows.
core::Result<void> sync_directory(const core::fs::path& path);
core::Result<void> write_new(const core::fs::path& path, const std::string& bytes,
                             unsigned mode = 0600);
core::Result<void> private_umask();
core::Result<void> check_private_directory(const core::fs::path& path);

class Lock {
  public:
    static core::Result<Lock> acquire(const core::fs::path& root);
    ~Lock();
    Lock(Lock&&) noexcept;
    Lock& operator=(Lock&&) noexcept;
    Lock(const Lock&) = delete;
    Lock& operator=(const Lock&) = delete;

  private:
    struct Impl;
    explicit Lock(std::unique_ptr<Impl> implementation);
    std::unique_ptr<Impl> implementation_;
};
} // namespace aslice::platform

#endif // ASLICE_PLATFORM_FILESYSTEM_HPP
