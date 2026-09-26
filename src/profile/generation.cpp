#include "profile/generation.hpp"
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include "resolver/solver.hpp"
#include "store/fixture_store.hpp"
#include <cstdlib>
#include <filesystem>
#include <set>
#include <string>
#include <string_view>

namespace aslice::profile {
namespace fs = std::filesystem;
using core::Error;
using core::Json;
using core::no_symlinks;
using core::read_json;
using core::require;

using adapters::fixture::candidates;
using adapters::fixture::format;
using adapters::fixture::requested;
using adapters::fixture::serialize;
using platform::check_private_directory;
using platform::sync_directory;
using platform::write_new;
using resolver::collisions;
using resolver::consistent;
using store::import_package;
using store::verify_store;
void check_prefix_impl(const fs::path& root) {
    aslice::core::take(no_symlinks(root));
    core::take(check_private_directory(root));
    const auto marker = aslice::core::take(read_json(root / ".prototype.json"));
    require(marker.at("format") == format, "not a disposable aslice prototype prefix");
    for (const auto& part : {"store", "profiles", "profiles/generations"}) {
        aslice::core::take(no_symlinks(root / part));
        require(fs::is_directory(root / part), "missing prototype directory");
    }
}
std::string current_id_impl(const fs::path& root) {
    const auto link = root / "profiles/default";
    require(fs::is_symlink(fs::symlink_status(link)), "missing active generation pointer");
    const auto target = fs::read_symlink(link).generic_string();
    require(target.starts_with("generations/") && target.size() > 12 &&
                target.substr(12).find_first_not_of("0123456789") == std::string::npos,
            "invalid generation pointer");
    return target.substr(12);
}
adapters::fixture::Generation state_impl(const fs::path& root, const std::string& generation) {
    require(!generation.empty() && generation.find_first_not_of("0123456789") == std::string::npos,
            "invalid generation ID");
    const auto path = root / "profiles/generations" / generation;
    aslice::core::take(no_symlinks(path));
    const auto result = aslice::core::take(read_json(path / "state.json"));
    return core::take(adapters::fixture::Generation::parse(result, generation));
}
void switch_to_impl(const fs::path& root, const std::string& generation) {
    const auto next = root / "profiles/.next";
    // A crash may have left this pointer. Never follow it or remove a directory.
    if (fs::exists(fs::symlink_status(next))) {
        require(fs::is_symlink(fs::symlink_status(next)), "unexpected profile staging entry");
        fs::remove(next);
    }
    fs::create_symlink("generations/" + generation, next);
    core::take(sync_directory(root / "profiles"));
    const char* point = std::getenv("ASLICE_PROTOTYPE_FAILPOINT");
    if (point && std::string_view(point) == "before-switch") {
        throw Error("injected interruption before activation; old generation remains active", "io");
    }
    fs::rename(next, root / "profiles/default");
    core::take(sync_directory(root / "profiles"));
    if (point && std::string_view(point) == "after-switch") {
        throw Error(
            "injected interruption after activation; new generation is committed; inspect list",
            "io");
    }
}
std::string commit_impl(const fs::path& root, const adapters::fixture::Selection& selected,
                        const std::set<std::string>& roots, const std::string& parent) {
    require(consistent(candidates(selected)), "selected dependencies are inconsistent");
    aslice::core::take(collisions(candidates(selected)));
    for (const auto& [name, package] : selected) {
        (void)name;
        aslice::core::take(import_package(root, package));
    }
    const auto generations = root / "profiles/generations";
    std::size_t number = 1;
    while (fs::exists(generations / std::to_string(number)) ||
           fs::exists(generations / (".stage-" + std::to_string(number)))) {
        ++number;
    }
    const auto id = std::to_string(number);
    const auto staging = generations / (".stage-" + id);
    fs::create_directory(staging);
    for (const auto& [name, package] : selected) {
        (void)name;
        for (const auto& [path, file] : package.files()) {
            (void)file;
            fs::create_directories((staging / path).parent_path());
            fs::create_symlink(root / "store" / package.candidate().artifact() / path,
                               staging / path);
        }
    }
    core::take(
        write_new(staging / "state.json",
                  adapters::fixture::generation_document(id, parent, selected, roots).dump()));
    for (const auto& entry : fs::recursive_directory_iterator(staging)) {
        if (fs::is_directory(entry.symlink_status())) {
            core::take(sync_directory(entry.path()));
        }
    }
    core::take(sync_directory(staging));
    fs::rename(staging, generations / id);
    core::take(sync_directory(generations));
    aslice::core::take(switch_to(root, id));
    return id;
}
void verify_generation_impl(const fs::path& root, const std::string& id,
                            const adapters::fixture::Selection& selected) {
    require(consistent(candidates(selected)), "generation dependency mismatch");
    aslice::core::take(collisions(candidates(selected)));
    for (const auto& [name, package] : selected) {
        (void)name;
        aslice::core::take(verify_store(root, package));
        for (const auto& [path, file] : package.files()) {
            (void)file;
            const auto link = root / "profiles/generations" / id / path;
            aslice::core::take(no_symlinks(link.parent_path()));
            require(fs::is_symlink(fs::symlink_status(link)) &&
                        fs::read_symlink(link) ==
                            root / "store" / package.candidate().artifact() / path,
                    "generation link mismatch: " + path);
        }
    }
}

core::Result<void> check_prefix(const fs::path& root) {
    return core::capture([&] {
        return check_prefix_impl(root);
    });
}

core::Result<std::string> current_id(const fs::path& root) {
    return core::capture([&] {
        return current_id_impl(root);
    });
}

core::Result<adapters::fixture::Generation> state(const fs::path& root,
                                                  const std::string& generation) {
    return core::capture([&] {
        return state_impl(root, generation);
    });
}

core::Result<void> switch_to(const fs::path& root, const std::string& generation) {
    return core::capture([&] {
        return switch_to_impl(root, generation);
    });
}

core::Result<std::string> commit(const fs::path& root, const adapters::fixture::Selection& selected,
                                 const std::set<std::string>& roots, const std::string& parent) {
    return core::capture([&] {
        return commit_impl(root, selected, roots, parent);
    });
}

core::Result<void> verify_generation(const fs::path& root, const std::string& id,
                                     const adapters::fixture::Selection& selected) {
    return core::capture([&] {
        return verify_generation_impl(root, id, selected);
    });
}
} // namespace aslice::profile
