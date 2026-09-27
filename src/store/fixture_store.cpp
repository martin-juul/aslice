#include "store/fixture_store.hpp"
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <set>
#include <string>
#include <vector>

namespace aslice::store {
using core::require;

using adapters::fixture::Package;
using platform::NodeKind;
void verify_store_impl(platform::FileSystem& filesystem, const platform::TargetPath& root,
                       const Package& package) {
    const auto directory = root / "store" / package.candidate().artifact();
    filesystem.no_symlinks(directory);
    require(filesystem.read_json(directory / ".package.json") == package.document(),
            "store metadata mismatch: " + package.candidate().name());
    std::set<std::string> expected{".package.json"};
    for (const auto& [path, file] : package.files()) {
        const auto full = directory / path;
        filesystem.no_symlinks(full);
        require(filesystem.read(full, 65536) == file.text, "store corruption: " + path);
        const auto mode = filesystem.status(full).mode;
        require(mode == (file.executable ? 0500U : 0400U), "store mode mismatch: " + path);
        expected.insert(path);
    }
    for (const auto& entry : filesystem.walk(directory)) {
        const auto kind = filesystem.status(entry).kind;
        require(kind != NodeKind::symlink, "store symlink refused");
        if (kind != NodeKind::directory) {
            require(expected.contains(entry.relative_to(directory)), "unexpected store entry");
        }
    }
}
void import_package_impl(platform::FileSystem& filesystem, const platform::TargetPath& root,
                         const Package& package) {
    const auto destination = root / "store" / package.candidate().artifact();
    if (filesystem.exists(destination)) {
        aslice::core::take(verify_store(filesystem, root, package));
        return;
    }
    const auto staging = root / "store" / (".stage-" + package.candidate().artifact());
    require(!filesystem.exists(staging),
            "unfinished store staging exists; use a fresh disposable prefix");
    filesystem.mkdir(staging);
    filesystem.write_new(staging / ".package.json", package.document().dump(), 0400);
    for (const auto& [path, file] : package.files()) {
        filesystem.create_directories((staging / path).parent_path());
        filesystem.write_new(staging / path, file.text, file.executable ? 0500 : 0400);
    }
    std::vector<platform::TargetPath> directories{staging};
    for (const auto& entry : filesystem.walk(staging)) {
        if (filesystem.status(entry).kind == NodeKind::directory) {
            directories.push_back(entry);
        }
    }
    for (auto it = directories.rbegin(); it != directories.rend(); ++it) {
        filesystem.permissions(*it, 0500);
        filesystem.sync_directory(*it);
    }
    filesystem.rename(staging, destination);
    filesystem.sync_directory(root / "store");
    aslice::core::take(verify_store(filesystem, root, package));
}

core::Result<void> verify_store(platform::FileSystem& filesystem, const platform::TargetPath& root,
                                const Package& package) {
    return core::capture([&] {
        return verify_store_impl(filesystem, root, package);
    });
}

core::Result<void> import_package(platform::FileSystem& filesystem,
                                  const platform::TargetPath& root, const Package& package) {
    return core::capture([&] {
        return import_package_impl(filesystem, root, package);
    });
}
} // namespace aslice::store
