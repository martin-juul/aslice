#ifndef ASLICE_PLATFORM_TARGET_FILESYSTEM_HPP
#define ASLICE_PLATFORM_TARGET_FILESYSTEM_HPP
#include "core/support.hpp"
#include "platform/paths.hpp"
#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::platform {
enum class NodeKind : std::uint8_t { missing, file, directory, symlink, other };
struct NodeStatus {
    NodeKind kind = NodeKind::missing;
    unsigned mode = 0;
    std::uint64_t links = 0;
};
class FileLock {
  public:
    virtual ~FileLock() = default;
};
// Operations throw core::Error at the platform boundary. Application public
// entry points retain their existing Result<T> error contracts.
class FileSystem {
  public:
    virtual ~FileSystem() = default;
    virtual bool supports_prefix_operations() const = 0;
    virtual TargetPath absolute(const std::string& path) const = 0;
    virtual std::string display_path(const TargetPath& path) const {
        return path.string();
    }
    virtual NodeStatus status(const TargetPath& path) = 0; // never follows links
    virtual std::vector<TargetPath> list(const TargetPath& path) = 0;
    using Consumer = std::function<void(std::string_view)>;
    using Inspector = std::function<void(const NodeStatus&)>;
    virtual bool supports_posix_modes() const = 0;
    virtual void stream(const TargetPath& path, std::size_t maximum, const Consumer& consume,
                        const Inspector& inspect = {}) = 0;
    std::string read(const TargetPath& path, std::size_t maximum);
    virtual void mkdir(const TargetPath& path) = 0;
    virtual void permissions(const TargetPath& path, unsigned mode) = 0;
    virtual void create_symlink(const std::string& target, const TargetPath& path) = 0;
    virtual std::string read_symlink(const TargetPath& path) = 0;
    virtual void rename(const TargetPath& source, const TargetPath& destination) = 0;
    virtual void remove(const TargetPath& path) = 0;
    virtual void write_new(const TargetPath& path, const std::string& bytes,
                           unsigned mode = 0600) = 0;
    virtual void sync_directory(const TargetPath& path) = 0;
    virtual void private_umask() = 0;
    virtual void check_private_directory(const TargetPath& path) = 0;
    virtual std::unique_ptr<FileLock> lock(const TargetPath& root) = 0;
    virtual void checkpoint(const std::string& name) = 0;

    bool exists(const TargetPath& path);
    void no_symlinks(const TargetPath& path);
    void create_directories(const TargetPath& path);
    std::vector<TargetPath> walk(const TargetPath& path);
    core::Json read_json(const TargetPath& path);
};

class NativeFileSystem final : public FileSystem {
  public:
    bool supports_prefix_operations() const override;
    TargetPath absolute(const std::string& path) const override;
    std::string display_path(const TargetPath& path) const override;
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
};
} // namespace aslice::platform
#endif
