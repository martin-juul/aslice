#ifndef ASLICE_PLATFORM_PATHS_HPP
#define ASLICE_PLATFORM_PATHS_HPP
#include "core/support.hpp"
#include <filesystem>
#include <string>
#include <utility>

namespace aslice::platform {
// A target path is never interpreted by std::filesystem or the host OS.
class TargetPath {
  public:
    explicit TargetPath(std::string value) : value_(std::move(value)) {
        core::require(!value_.empty() && value_.front() == '/' &&
                          value_.find('\0') == std::string::npos &&
                          value_.find('\\') == std::string::npos,
                      "target path must be absolute POSIX syntax");
        if (value_ != "/") {
            core::require(value_.back() != '/', "target path has trailing slash");
            std::size_t start = 1;
            while (start < value_.size()) {
                const auto end = value_.find('/', start);
                const auto part = value_.substr(start, end - start);
                core::require(!part.empty() && part != "." && part != "..",
                              "target path is not canonical");
                if (end == std::string::npos) {
                    break;
                }
                start = end + 1;
            }
        }
    }
    const std::string& string() const {
        return value_;
    }
    TargetPath operator/(const std::string& relative) const {
        core::require(!relative.empty() && relative.front() != '/',
                      "expected a relative target path");
        return TargetPath{value_ == "/" ? "/" + relative : value_ + "/" + relative};
    }
    TargetPath parent_path() const {
        const auto slash = value_.find_last_of('/');
        return TargetPath{slash == 0 ? "/" : value_.substr(0, slash)};
    }
    std::string filename() const {
        return value_.substr(value_.find_last_of('/') + 1);
    }
    std::string relative_to(const TargetPath& parent) const {
        const auto prefix = parent.string() == "/" ? "/" : parent.string() + "/";
        core::require(value_.starts_with(prefix), "target is outside its parent");
        return value_.substr(prefix.size());
    }
    bool operator==(const TargetPath&) const = default;

  private:
    std::string value_;
};

class HostPath {
  public:
    explicit HostPath(std::filesystem::path value) : value_(std::move(value)) {}
    const std::filesystem::path& path() const {
        return value_;
    }

  private:
    std::filesystem::path value_;
};
} // namespace aslice::platform
#endif
