#include "cli/registry.hpp"

#include "adapters/fixture.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "platform/filesystem.hpp"
#include "profile/generation.hpp"
#include "resolver/solver.hpp"
#include <filesystem>
#include <functional>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace aslice::cli {
namespace fs = std::filesystem;
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
using core::no_symlinks;
using core::read_json;
using core::require;
using package::flavor_rank;
using package::key;
using package::os_rank;
using package::Target;
using platform::Lock;
using platform::private_umask;
using platform::sync_directory;
using platform::write_new;
using profile::check_prefix;
using profile::commit;
using profile::current_id;
using profile::state;
using profile::switch_to;
using profile::verify_generation;
using resolver::consistent;
namespace {
int initialize_fixture(const fs::path& prefix, const std::string& target_os,
                       const std::string& flavor) {
    const std::string command = "init";

    core::take(os_rank(target_os));
    core::take(flavor_rank(flavor));
    require(!fs::exists(prefix),
            "prototype init requires a new prefix; existing paths are never adopted");
    require(fs::is_directory(prefix.parent_path()), "prefix parent must already exist");
    fs::create_directory(prefix);
    fs::permissions(prefix, fs::perms::owner_all);
    fs::create_directory(prefix / "store");
    fs::create_directories(prefix / "profiles/generations");
    core::take(write_new(prefix / ".prototype.json",
                         Json{{"format", format}, {"os", target_os}, {"flavor", flavor}}.dump()));
    core::take(write_new(prefix / ".lock", ""));
    core::take(sync_directory(prefix));
    core::take(sync_directory(prefix.parent_path()));
    auto lock = core::take(Lock::acquire(prefix));
    const auto id = aslice::core::take(commit(prefix, {}, {}, ""));
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
    fs::path prefix = invocation.option("--prefix");
    fs::path catalog = invocation.option("--catalog");
    const auto command = invocation.command.substr(invocation.command.find_last_of(' ') + 1);
    const auto target_os = invocation.option("--target-os", "10.11");
    const auto flavor = invocation.option("--flavor", "v1");
    const auto& arguments = invocation.arguments;
    const bool dry = invocation.options.contains("--dry-run");
    prefix = fs::absolute(prefix).lexically_normal();
    aslice::core::take(no_symlinks(prefix));
    core::take(private_umask());
    if (command == "init") {
        return initialize_fixture(prefix, target_os, flavor);
    }

    aslice::core::take(check_prefix(prefix));
    auto lock = core::take(Lock::acquire(prefix));
    const auto id = aslice::core::take(current_id(prefix));
    const auto old = aslice::core::take(state(prefix, id));
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
        for (const auto& entry : fs::directory_iterator(prefix / "profiles/generations")) {
            const auto name = entry.path().filename().string();
            if (!name.empty() && name.find_first_not_of("0123456789") == std::string::npos) {
                const auto data = aslice::core::take(state(prefix, name));
                output["generations"].push_back(
                    {{"id", name},
                     {"active", name == id},
                     {"packages", summary(data.selected(), data.roots())}});
            }
        }
    } else if (command == "verify") {
        aslice::core::take(verify_generation(prefix, id, installed));
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
        const auto previous = aslice::core::take(state(prefix, arguments[0]));
        const auto& chosen = previous.selected();
        aslice::core::take(verify_generation(prefix, arguments[0], chosen));
        output["target_generation"] = arguments[0];
        output["dry_run"] = dry;
        if (!dry) {
            aslice::core::take(switch_to(prefix, arguments[0]));
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
            auto packages =
                core::take(adapters::fixture::catalog(core::take(core::read_json(catalog))));
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
                    aslice::core::take(read_json(prefix / ".prototype.json")).at("os"),
                    aslice::core::take(read_json(prefix / ".prototype.json")).at("flavor")))));
        }
        output["packages"] = summary(chosen, roots);
        output["dry_run"] = dry || command == "plan";
        output["changed"] = serialize(chosen) != serialize(installed) || roots != old.roots();
        if (!output["dry_run"].get<bool>() && output["changed"].get<bool>()) {
            output["generation"] = aslice::core::take(commit(prefix, chosen, roots, id));
        }
    }
    std::cout << output.dump(2) << '\n';
    require(std::cout.good(), "cannot write command output");
    return 0;
}
} // namespace aslice::cli
