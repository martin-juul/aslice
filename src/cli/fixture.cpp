#include "cli/registry.hpp"

#include "adapters/fixture.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include "profile/generation.hpp"
#include "resolver/solver.hpp"
#include <functional>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace aslice::cli {
using adapters::fixture::candidates;
using adapters::fixture::catalog;
using adapters::fixture::format;
using adapters::fixture::Package;
using adapters::fixture::requested;
using adapters::fixture::selection;
using adapters::fixture::serialize;
using adapters::fixture::summary;
using core::fields;
using core::Json;
using core::require;
using package::flavor_rank;
using package::key;
using package::os_rank;
using package::Target;
using platform::NodeKind;
using profile::check_prefix;
using profile::commit;
using profile::current_id;
using profile::state;
using profile::switch_to;
using profile::verify_generation;
using resolver::consistent;
namespace {
int initialize_fixture(platform::FileSystem& filesystem, const platform::TargetPath& prefix,
                       const std::string& target_os, const std::string& flavor) {
    const std::string command = "init";

    core::take(os_rank(target_os));
    core::take(flavor_rank(flavor));
    require(!filesystem.exists(prefix),
            "prototype init requires a new prefix; existing paths are never adopted");
    require(filesystem.status(prefix.parent_path()).kind == NodeKind::directory,
            "prefix parent must already exist");
    filesystem.mkdir(prefix);
    filesystem.permissions(prefix, 0700);
    filesystem.mkdir(prefix / "store");
    filesystem.create_directories(prefix / "profiles/generations");
    filesystem.write_new(prefix / ".prototype.json",
                         Json{{"format", format}, {"os", target_os}, {"flavor", flavor}}.dump());
    filesystem.write_new(prefix / ".lock", "");
    filesystem.sync_directory(prefix);
    filesystem.sync_directory(prefix.parent_path());
    auto lock = filesystem.lock(prefix);
    const auto id = aslice::core::take(commit(filesystem, prefix, {}, {}, ""));
    std::cout << Json{{"format", format},
                      {"command", command},
                      {"generation", id},
                      {"prefix", prefix.string()}}
                     .dump(2)
              << '\n';
    return 0;
}
} // namespace
int fixture(const Invocation& invocation) {
    auto& filesystem = invocation.filesystem;
    const auto prefix = filesystem.absolute(invocation.option("--prefix"));
    const auto catalog = invocation.option("--catalog");
    const auto command = invocation.command.substr(invocation.command.find_last_of(' ') + 1);
    const auto target_os = invocation.option("--target-os", "10.11");
    const auto flavor = invocation.option("--flavor", "v1");
    const auto& arguments = invocation.arguments;
    const bool dry = invocation.options.contains("--dry-run");
    filesystem.no_symlinks(prefix);
    filesystem.private_umask();
    if (command == "init") {
        return initialize_fixture(filesystem, prefix, target_os, flavor);
    }

    aslice::core::take(check_prefix(filesystem, prefix));
    auto lock = filesystem.lock(prefix);
    const auto id = aslice::core::take(current_id(filesystem, prefix));
    const auto old = aslice::core::take(state(filesystem, prefix, id));
    auto installed = old.selected();
    auto roots = old.roots();
    for (const auto& name : roots) {
        require(installed.contains(name), "requested package is absent from generation");
    }
    Json output{{"format", format}, {"command", command}, {"generation", id}};
    if (command == "list") {
        output["packages"] = summary(installed, roots);
    } else if (command == "history") {
        output["generations"] = Json::array();
        for (const auto& entry : filesystem.list(prefix / "profiles/generations")) {
            const auto name = entry.filename();
            if (!name.empty() && name.find_first_not_of("0123456789") == std::string::npos) {
                const auto data = aslice::core::take(state(filesystem, prefix, name));
                output["generations"].push_back(
                    {{"id", name},
                     {"active", name == id},
                     {"packages", summary(data.selected(), data.roots())}});
            }
        }
    } else if (command == "verify") {
        aslice::core::take(verify_generation(filesystem, prefix, id, installed));
        output["verified"] = true;
    } else if (command == "why" || command == "leaves") {
        std::set<std::string> dependencies;
        Json dependents = Json::array();
        if (command == "why") {
            require(installed.contains(core::take(key(arguments[0]))), "package is not installed");
        }
        for (const auto& [name, package] : installed) {
            for (const auto& [dependency, constraint] : package.candidate().dependencies()) {
                (void)constraint;
                dependencies.insert(dependency);
                if (command == "why" && dependency == core::take(key(arguments[0]))) {
                    dependents.push_back(name);
                }
            }
        }
        if (command == "why") {
            output["requested"] = roots.contains(core::take(key(arguments[0])));
            output["dependents"] = dependents;
        } else {
            output["packages"] = Json::array();
            for (const auto& [name, package] : installed) {
                (void)package;
                if (!dependencies.contains(name)) {
                    output["packages"].push_back(name);
                }
            }
        }
    } else if (command == "rollback") {
        const auto previous = aslice::core::take(state(filesystem, prefix, arguments[0]));
        const auto& chosen = previous.selected();
        aslice::core::take(verify_generation(filesystem, prefix, arguments[0], chosen));
        output["target_generation"] = arguments[0];
        output["dry_run"] = dry;
        if (!dry) {
            aslice::core::take(switch_to(filesystem, prefix, arguments[0]));
            output["generation"] = arguments[0];
        }
    } else {
        adapters::fixture::Selection chosen = installed;
        if (command == "uninstall") {
            for (const auto& name : arguments) {
                require(chosen.erase(core::take(key(name))) == 1,
                        "package is not installed: " + name);
                roots.erase(core::take(key(name)));
            }
            require(consistent(candidates(chosen)),
                    "uninstall would break an installed dependency; remove its dependents too");
        } else if (command == "autoremove") {
            std::set<std::string> live;
            std::function<void(const std::string&)> visit = [&](const std::string& name) {
                require(chosen.contains(name), "missing installed dependency");
                if (!live.insert(name).second) {
                    return;
                }
                for (const auto& [dependency, constraint] :
                     chosen.at(name).candidate().dependencies()) {
                    (void)constraint;
                    visit(dependency);
                }
            };
            for (const auto& root : roots) {
                visit(root);
            }
            std::erase_if(chosen, [&](const auto& entry) {
                return !live.contains(entry.first);
            });
        } else {
            require(!catalog.empty(), "--catalog is required for this fixture operation");
            auto packages = core::take(
                adapters::fixture::catalog(filesystem.read_json(filesystem.absolute(catalog))));
            std::set<std::string> identities;
            for (const auto& package : packages) {
                identities.insert(package.candidate().artifact());
            }
            if (command == "search" || command == "info") {
                output["packages"] = Json::array();
                for (const auto& package : packages) {
                    if (command == "search"
                            ? package.candidate().name().find(arguments[0]) != std::string::npos
                            : package.candidate().name() == core::take(key(arguments[0]))) {
                        output["packages"].push_back(package.document());
                    }
                }
                std::cout << output.dump(2) << '\n';
                return 0;
            }
            for (const auto& [name, package] : installed) {
                (void)name;
                if (identities.insert(package.candidate().artifact()).second) {
                    packages.push_back(package);
                }
            }
            for (const auto& name : arguments) {
                roots.insert(core::take(key(name)));
            }
            chosen = aslice::core::take(adapters::fixture::resolve(
                packages, roots, installed,
                command == "upgrade" ? resolver::Preference::newest
                                     : resolver::Preference::installed,
                core::take(Target::create(
                    filesystem.read_json(prefix / ".prototype.json").at("os"),
                    filesystem.read_json(prefix / ".prototype.json").at("flavor")))));
        }
        output["packages"] = summary(chosen, roots);
        output["dry_run"] = dry || command == "plan";
        output["changed"] = serialize(chosen) != serialize(installed) || roots != old.roots();
        if (!output["dry_run"].get<bool>() && output["changed"].get<bool>()) {
            output["generation"] =
                aslice::core::take(commit(filesystem, prefix, chosen, roots, id));
        } else if (!output["dry_run"].get<bool>()) {
            // Activation may have changed the live link but lost its acknowledgement
            // before the directory flush. Verify before confirming a durable no-op.
            aslice::core::take(verify_generation(filesystem, prefix, id, installed));
            filesystem.sync_directory(prefix / "profiles");
        }
    }
    std::cout << output.dump(2) << '\n';
    require(std::cout.good(), "cannot write command output");
    return 0;
}
} // namespace aslice::cli
