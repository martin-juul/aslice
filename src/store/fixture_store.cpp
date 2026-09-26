#include "store/fixture_store.hpp"
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/filesystem.hpp"
#include <filesystem>
#include <set>
#include <string>
#include <vector>

namespace aslice::store {
namespace fs = std::filesystem;
using core::no_symlinks;
using core::read_bytes;
using core::read_json;
using core::require;

using adapters::fixture::Package;
using platform::sync_directory;
using platform::write_new;
void verify_store_impl(const fs::path& root, const Package& package) {
    const auto directory = root / "store" / package.candidate().artifact();
    aslice::core::take(no_symlinks(directory));
    require(aslice::core::take(read_json(directory / ".package.json")) == package.document(),
            "store metadata mismatch: " + package.candidate().name());
    std::set<std::string> expected{".package.json"};
    for (const auto& [path, file] : package.files()) {
        const auto full = directory / path;
        aslice::core::take(no_symlinks(full));
        require(aslice::core::take(read_bytes(full, 65536)) == file.text,
                "store corruption: " + path);
        const auto mode = fs::status(full).permissions() & fs::perms::all;
        require(mode == (file.executable ? fs::perms::owner_read | fs::perms::owner_exec
                                         : fs::perms::owner_read),
                "store mode mismatch: " + path);
        expected.insert(path);
    }
    for (const auto& entry : fs::recursive_directory_iterator(directory)) {
        require(!entry.is_symlink(), "store symlink refused");
        if (!entry.is_directory()) {
            require(expected.contains(entry.path().lexically_relative(directory).generic_string()),
                    "unexpected store entry");
        }
    }
}
void import_package_impl(const fs::path& root, const Package& package) {
    const auto destination = root / "store" / package.candidate().artifact();
    if (fs::exists(destination)) {
        aslice::core::take(verify_store(root, package));
        return;
    }
    const auto staging = root / "store" / (".stage-" + package.candidate().artifact());
    require(!fs::exists(fs::symlink_status(staging)),
            "unfinished store staging exists; use a fresh disposable prefix");
    fs::create_directory(staging);
    core::take(write_new(staging / ".package.json", package.document().dump(), 0400));
    for (const auto& [path, file] : package.files()) {
        fs::create_directories((staging / path).parent_path());
        core::take(write_new(staging / path, file.text, file.executable ? 0500 : 0400));
    }
    std::vector<fs::path> directories{staging};
    for (const auto& entry : fs::recursive_directory_iterator(staging)) {
        if (entry.is_directory()) {
            directories.push_back(entry.path());
        }
    }
    for (auto it = directories.rbegin(); it != directories.rend(); ++it) {
        fs::permissions(*it, fs::perms::owner_read | fs::perms::owner_exec);
        core::take(sync_directory(*it));
    }
    fs::rename(staging, destination);
    core::take(sync_directory(root / "store"));
    aslice::core::take(verify_store(root, package));
}

core::Result<void> verify_store(const fs::path& root, const Package& package) {
    return core::capture([&] {
        return verify_store_impl(root, package);
    });
}

core::Result<void> import_package(const fs::path& root, const Package& package) {
    return core::capture([&] {
        return import_package_impl(root, package);
    });
}
} // namespace aslice::store
