#include "platform/target_filesystem.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::platform {
std::string FileSystem::read(const TargetPath& path, std::size_t maximum) {
    std::string result;
    stream(path, maximum, [&](std::string_view bytes) {
        result.append(bytes);
    });
    return result;
}
bool FileSystem::exists(const TargetPath& path) {
    return status(path).kind != NodeKind::missing;
}
void FileSystem::no_symlinks(const TargetPath& path) {
    std::vector<TargetPath> parents;
    auto current = path;
    while (current.string() != "/") {
        parents.push_back(current);
        current = current.parent_path();
    }
    for (auto it = parents.rbegin(); it != parents.rend(); ++it) {
        const auto kind = status(*it).kind;
        core::require(kind != NodeKind::symlink,
                      "symlinked prototype path refused: " + it->string());
        if (kind == NodeKind::missing) {
            break;
        }
    }
}
void FileSystem::create_directories(const TargetPath& path) {
    std::vector<TargetPath> missing;
    auto current = path;
    while (status(current).kind == NodeKind::missing) {
        core::require(current.string() != "/", "missing target root");
        missing.push_back(current);
        current = current.parent_path();
    }
    core::require(status(current).kind == NodeKind::directory, "parent is not a directory");
    for (auto it = missing.rbegin(); it != missing.rend(); ++it) {
        mkdir(*it);
    }
}
std::vector<TargetPath> FileSystem::walk(const TargetPath& path) {
    std::vector<TargetPath> result;
    std::vector<TargetPath> pending{path};
    for (std::size_t i = 0; i < pending.size(); ++i) {
        for (const auto& child : list(pending[i])) {
            core::require(result.size() < 100000, "filesystem walk exceeds fixture limit");
            result.push_back(child);
            if (status(child).kind == NodeKind::directory) {
                pending.push_back(child);
            }
        }
    }
    return result;
}
core::Json FileSystem::read_json(const TargetPath& path) {
    return core::take(core::parse_json(read(path, 4 * 1024 * 1024)));
}
} // namespace aslice::platform
