#include "adapters/fixture.hpp"
#include "cli/registry.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "package/manifest.hpp"
#include "package/slice.hpp"
#include "package/version.hpp"
#include "platform/target_filesystem.hpp"
#include "resolver/solver.hpp"
#include <iostream>
#include <set>
#include <zstd.h>

namespace aslice::cli {
int inspect(const Invocation& invocation) {
    using adapters::fixture::catalog;
    using adapters::fixture::format;
    using adapters::fixture::summary;
    using core::digest;
    using core::Error;
    using core::Json;
    using core::require;
    using package::Constraint;
    using package::flavor_rank;
    using package::inspect_slice;
    using package::key;
    using package::Manifest;
    using package::os_rank;
    using package::pack_slice;
    using package::Target;
    using package::Version;
    using package::version;
    const auto& command = invocation.command;
    const auto& args = invocation.arguments;
    auto& filesystem = invocation.filesystem;
    Json output;
    if (command == "slice inspect") {
        output = aslice::core::take(inspect_slice(filesystem, filesystem.absolute(args[0])));
    } else if (command == "slice pack") {
        const auto manifest =
            core::take(Manifest::parse(filesystem.read_json(filesystem.absolute(args[0]))));
        const auto path = filesystem.absolute(args[2]);
        filesystem.no_symlinks(path.parent_path());
        require(!filesystem.exists(path), "output already exists; refusing to replace it");
        const auto bytes =
            aslice::core::take(pack_slice(filesystem, manifest, filesystem.absolute(args[1])));
        filesystem.write_new(path, bytes, 0600);
        output = {{"artifact_id", manifest.artifact_id()},
                  {"blob_digest", "sha256:" + aslice::core::take(digest(bytes))},
                  {"blob_size", bytes.size()},
                  {"authenticated", false},
                  {"output", filesystem.display_path(path)},
                  {"packer", "aslice-prototype-zstd-level3"},
                  {"zstd_version", ZSTD_versionString()}};
    } else if (command == "artifact inspect" || command == "artifact verify") {
        const auto manifest =
            core::take(Manifest::parse(filesystem.read_json(filesystem.absolute(args[0]))));
        output = command == "artifact verify"
                     ? aslice::core::take(manifest.verify_payload(
                           filesystem, filesystem.absolute(invocation.option("--payload"))))
                     : manifest.inspect();
    } else if (command.starts_with("version ")) {
        const auto operation = command.substr(8);
        if (operation == "normalize") {
            output = {{"version", aslice::core::take(Version::normalize(args[0])).string()}};
        } else if (operation == "compare") {
            const auto order = aslice::core::take(Version::parse(args[0])) <=>
                               aslice::core::take(Version::parse(args[1]));
            output = {{"order", order < 0 ? -1 : order > 0 ? 1 : 0}};
        } else {
            output = {{"matches", aslice::core::take(Constraint::parse(args[1]))
                                      .matches(aslice::core::take(Version::parse(args[0])))}};
        }
    } else {
        Json target{{"os", invocation.option("--target-os", "10.11")},
                    {"flavor", invocation.option("--flavor", "v1")}};
        const auto file = filesystem.absolute(invocation.option("--catalog"));
        std::set<std::string> roots;
        for (const auto& argument : args) {
            roots.insert(core::take(key(argument)));
        }
        const bool prerelease = invocation.options.contains("--prerelease");
        core::take(os_rank(target["os"]));
        core::take(flavor_rank(target["flavor"]));
        const auto selected = aslice::core::take(adapters::fixture::resolve(
            aslice::core::take(catalog(filesystem.read_json(file))), roots, {},
            resolver::Preference::newest,
            core::take(Target::create(target["os"], target["flavor"])),
            prerelease ? package::PrereleasePolicy::allow : package::PrereleasePolicy::normal));
        output = {{"format", format}, {"packages", summary(selected, roots)}, {"target", target}};
    }
    std::cout << output.dump(2) << '\n';
    require(std::cout.good(), "cannot write output");
    return 0;
}
} // namespace aslice::cli
