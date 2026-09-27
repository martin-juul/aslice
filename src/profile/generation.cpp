#include "profile/generation.hpp"
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include "resolver/solver.hpp"
#include "store/fixture_store.hpp"
#include <cstddef>
#include <set>
#include <string>

namespace aslice::profile {
using core::require;

using adapters::fixture::candidates;
using adapters::fixture::format;
using adapters::fixture::requested;
using adapters::fixture::serialize;
using platform::NodeKind;
using resolver::collisions;
using resolver::consistent;
using store::import_package;
using store::verify_store;
void check_prefix_impl(platform::FileSystem& filesystem, const platform::TargetPath& root) {
    filesystem.no_symlinks(root);
    filesystem.check_private_directory(root);
    const auto marker = filesystem.read_json(root / ".prototype.json");
    require(marker.at("format") == format, "not a disposable aslice prototype prefix");
    for (const auto& part : {"store", "profiles", "profiles/generations"}) {
        filesystem.no_symlinks(root / part);
        require(filesystem.status(root / part).kind == NodeKind::directory,
                "missing prototype directory");
    }
}
std::string current_id_impl(platform::FileSystem& filesystem, const platform::TargetPath& root) {
    const auto link = root / "profiles/default";
    require(filesystem.status(link).kind == NodeKind::symlink, "missing active generation pointer");
    const auto target = filesystem.read_symlink(link);
    require(target.starts_with("generations/") && target.size() > 12 &&
                target.substr(12).find_first_not_of("0123456789") == std::string::npos,
            "invalid generation pointer");
    return target.substr(12);
}
adapters::fixture::Generation state_impl(platform::FileSystem& filesystem,
                                         const platform::TargetPath& root,
                                         const std::string& generation) {
    require(!generation.empty() && generation.find_first_not_of("0123456789") == std::string::npos,
            "invalid generation ID");
    const auto path = root / "profiles/generations" / generation;
    filesystem.no_symlinks(path);
    const auto result = filesystem.read_json(path / "state.json");
    return core::take(adapters::fixture::Generation::parse(result, generation));
}
void switch_to_impl(platform::FileSystem& filesystem, const platform::TargetPath& root,
                    const std::string& generation) {
    const auto next = root / "profiles/.next";
    // A crash may have left this pointer. Never follow it or remove a directory.
    if (filesystem.exists(next)) {
        require(filesystem.status(next).kind == NodeKind::symlink,
                "unexpected profile staging entry");
        filesystem.remove(next);
    }
    filesystem.create_symlink("generations/" + generation, next);
    filesystem.sync_directory(root / "profiles");
    filesystem.checkpoint("before-switch");
    filesystem.rename(next, root / "profiles/default");
    filesystem.sync_directory(root / "profiles");
    filesystem.checkpoint("after-switch");
}
std::string commit_impl(platform::FileSystem& filesystem, const platform::TargetPath& root,
                        const adapters::fixture::Selection& selected,
                        const std::set<std::string>& roots, const std::string& parent) {
    require(consistent(candidates(selected)), "selected dependencies are inconsistent");
    aslice::core::take(collisions(candidates(selected)));
    for (const auto& [name, package] : selected) {
        (void)name;
        aslice::core::take(import_package(filesystem, root, package));
    }
    const auto generations = root / "profiles/generations";
    std::size_t number = 1;
    while (filesystem.exists(generations / std::to_string(number)) ||
           filesystem.exists(generations / (".stage-" + std::to_string(number)))) {
        ++number;
    }
    const auto id = std::to_string(number);
    const auto staging = generations / (".stage-" + id);
    filesystem.mkdir(staging);
    for (const auto& [name, package] : selected) {
        (void)name;
        for (const auto& [path, file] : package.files()) {
            (void)file;
            filesystem.create_directories((staging / path).parent_path());
            filesystem.create_symlink(
                (root / "store" / package.candidate().artifact() / path).string(), staging / path);
        }
    }
    filesystem.write_new(
        staging / "state.json",
        adapters::fixture::generation_document(id, parent, selected, roots).dump());
    for (const auto& entry : filesystem.walk(staging)) {
        if (filesystem.status(entry).kind == NodeKind::directory) {
            filesystem.sync_directory(entry);
        }
    }
    filesystem.sync_directory(staging);
    filesystem.rename(staging, generations / id);
    filesystem.sync_directory(generations);
    aslice::core::take(switch_to(filesystem, root, id));
    return id;
}
void verify_generation_impl(platform::FileSystem& filesystem, const platform::TargetPath& root,
                            const std::string& id, const adapters::fixture::Selection& selected) {
    require(consistent(candidates(selected)), "generation dependency mismatch");
    aslice::core::take(collisions(candidates(selected)));
    for (const auto& [name, package] : selected) {
        (void)name;
        aslice::core::take(verify_store(filesystem, root, package));
        for (const auto& [path, file] : package.files()) {
            (void)file;
            const auto link = root / "profiles/generations" / id / path;
            filesystem.no_symlinks(link.parent_path());
            require(filesystem.status(link).kind == NodeKind::symlink &&
                        filesystem.read_symlink(link) ==
                            (root / "store" / package.candidate().artifact() / path).string(),
                    "generation link mismatch: " + path);
        }
    }
}

core::Result<void> check_prefix(platform::FileSystem& filesystem,
                                const platform::TargetPath& root) {
    return core::capture([&] {
        return check_prefix_impl(filesystem, root);
    });
}

core::Result<std::string> current_id(platform::FileSystem& filesystem,
                                     const platform::TargetPath& root) {
    return core::capture([&] {
        return current_id_impl(filesystem, root);
    });
}

core::Result<adapters::fixture::Generation> state(platform::FileSystem& filesystem,
                                                  const platform::TargetPath& root,
                                                  const std::string& generation) {
    return core::capture([&] {
        return state_impl(filesystem, root, generation);
    });
}

core::Result<void> switch_to(platform::FileSystem& filesystem, const platform::TargetPath& root,
                             const std::string& generation) {
    return core::capture([&] {
        return switch_to_impl(filesystem, root, generation);
    });
}

core::Result<std::string> commit(platform::FileSystem& filesystem, const platform::TargetPath& root,
                                 const adapters::fixture::Selection& selected,
                                 const std::set<std::string>& roots, const std::string& parent) {
    return core::capture([&] {
        return commit_impl(filesystem, root, selected, roots, parent);
    });
}

core::Result<void> verify_generation(platform::FileSystem& filesystem,
                                     const platform::TargetPath& root, const std::string& id,
                                     const adapters::fixture::Selection& selected) {
    return core::capture([&] {
        return verify_generation_impl(filesystem, root, id, selected);
    });
}
} // namespace aslice::profile
