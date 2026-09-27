#ifndef ASLICE_PLATFORM_TARGET_FILESYSTEM_REHEARSAL_HPP
#define ASLICE_PLATFORM_TARGET_FILESYSTEM_REHEARSAL_HPP
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/rehearsal.hpp"
#include "platform/target_filesystem.hpp"
#include <cstddef>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::platform {
class RehearsalFileSystem final : public FileSystem {
  public:
    explicit RehearsalFileSystem(Rehearsal& connection) : connection_(connection) {}
    bool supports_prefix_operations() const override;
    TargetPath absolute(const std::string& path) const override;
    NodeStatus status(const TargetPath& path) override;
    std::vector<TargetPath> list(const TargetPath& path) override;
    bool supports_posix_modes() const override;
    void stream(const TargetPath& path, std::size_t maximum, const Consumer& consume,
                const Inspector& inspect = {}) override;
    void mkdir(const TargetPath& path) override;
    void permissions(const TargetPath& path, unsigned mode) override;
    void create_symlink(const std::string& target, const TargetPath& path) override;
    std::string read_symlink(const TargetPath& path) override;
    void rename(const TargetPath& source, const TargetPath& destination) override;
    void remove(const TargetPath& path) override;
    void write_new(const TargetPath& path, const std::string& bytes, unsigned mode = 0600) override;
    void sync_directory(const TargetPath& path) override;
    void private_umask() override;
    void check_private_directory(const TargetPath& path) override;
    std::unique_ptr<FileLock> lock(const TargetPath& root) override;
    void checkpoint(const std::string& name) override;

  private:
    core::Json operation(const std::string& name, const TargetPath& path,
                         const core::Json& arguments = core::Json::object());
    Rehearsal& connection_;
};
} // namespace aslice::platform
#endif
