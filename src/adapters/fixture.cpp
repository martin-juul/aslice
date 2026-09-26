#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "package/version.hpp"
#include "resolver/solver.hpp"
#include "tl/expected.hpp"
#include <algorithm>
#include <exception>
#include <filesystem>
#include <iterator>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace aslice::adapters::fixture {
namespace fs = std::filesystem;
using core::digest;
using core::fields;
using core::Json;
using core::require;
using package::Constraint;
using package::flavor_rank;
using package::key;
using package::os_rank;
using package::version;
void payload_path(const std::string& path) {
    require(path.size() <= 240 &&
                path.find_first_not_of(
                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.+/") ==
                    std::string::npos,
            "payload paths must use portable ASCII characters: " + path);
    const fs::path p(path);
    require(p.is_relative() && !p.empty(), "payload path must be relative");
    require(p.lexically_normal().generic_string() == path && !path.ends_with('/'),
            "payload path must be normalized");
    for (const auto& part : p) {
        require(!part.empty() && part != "." && part != "..", "unsafe payload path: " + path);
    }
    const auto first = p.begin()->string();
    require(first == "bin" || first == "lib" || first == "share" || first == "include",
            "unsupported payload root: " + first);
    require(std::distance(p.begin(), p.end()) >= 2,
            "payload must be a file below a supported root");
}
core::Result<Package> Package::parse(Json data) {
    try {
        aslice::core::take(
            fields(data, {"name", "version", "flavor", "min_os", "dependencies", "files"}));
        const auto name = core::take(key(data.at("name").get<std::string>()));
        data["name"] = name;
        const auto release = data.at("version").get<std::string>();
        core::take(version(release));
        core::take(flavor_rank(data.at("flavor").get<std::string>()));
        core::take(os_rank(data.at("min_os").get<std::string>()));
        require(data.at("dependencies").is_object() && data.at("dependencies").size() <= 64,
                "invalid dependency map");
        Json dependencies = Json::object();
        for (const auto& [dependency, constraint] : data["dependencies"].items()) {
            const auto normalized = core::take(key(dependency));
            require(!dependencies.contains(normalized), "duplicate dependency name");
            aslice::core::take(Constraint::parse(constraint.get<std::string>()));
            dependencies[normalized] = constraint;
        }
        data["dependencies"] = dependencies;
        require(data.at("files").is_object() && data.at("files").size() <= 128,
                "invalid fixture file map");
        for (const auto& [path, file] : data["files"].items()) {
            payload_path(path);
            aslice::core::take(fields(file, {"text", "executable"}));
            require(file.at("text").is_string() &&
                        file.at("text").get_ref<const std::string&>().size() <= 65536 &&
                        file.at("executable").is_boolean(),
                    "invalid fixture file");
        }
        package::Dependencies typed_dependencies;
        for (const auto& [name, constraint] : data["dependencies"].items()) {
            typed_dependencies.emplace(
                name, core::take(Constraint::parse(constraint.get<std::string>())));
        }
        InlineFiles files;
        std::set<std::string> paths;
        for (const auto& [path, file] : data["files"].items()) {
            files.emplace(path, InlineFile{file.at("text"), file.at("executable")});
            paths.insert(path);
        }
        auto target = package::Target::create(data.at("min_os"), data.at("flavor"));
        if (!target) {
            return tl::unexpected(target.error());
        }
        auto candidate =
            package::Candidate::create(name, release, *target, std::move(typed_dependencies),
                                       std::move(paths), aslice::core::take(digest(data.dump())));
        if (!candidate) {
            return tl::unexpected(candidate.error());
        }
        return Package(std::move(data), std::move(*candidate), std::move(files));
    } catch (const std::exception& error) {
        return tl::unexpected(core::Failure{"invalid_fixture", error.what()});
    }
}
Selection selection_impl(const Json& value) {
    require(value.is_object() && value.size() <= 128, "invalid selected package map");
    Selection result;
    for (const auto& [name, raw] : value.items()) {
        auto package = core::take(Package::parse(raw));
        require(package.candidate().name() == name, "generation package name mismatch");
        result.emplace(name, std::move(package));
    }
    return result;
}
Json serialize(const Selection& selected) {
    Json result = Json::object();
    for (const auto& [name, package] : selected) {
        result[name] = package.document();
    }
    return result;
}
std::set<std::string> requested_impl(const Json& document) {
    require(document.at("requested").is_array(), "invalid requested set");
    std::set<std::string> result;
    for (const auto& name : document["requested"]) {
        result.insert(core::take(key(name.get<std::string>())));
    }
    return result;
}
Json summary(const Selection& selected, const std::set<std::string>& roots) {
    Json result = Json::array();
    for (const auto& [name, package] : selected) {
        result.push_back({{"name", name},
                          {"version", package.candidate().release()},
                          {"artifact", package.candidate().artifact()},
                          {"requested", roots.contains(name)}});
    }
    return result;
}
std::vector<Package> catalog_impl(const Json& document) {
    aslice::core::take(fields(document, {"format", "packages"}));
    require(document.at("format") == format && document.at("packages").is_array() &&
                document["packages"].size() <= 128,
            "invalid fixture catalog");
    std::vector<Package> result;
    std::set<std::string> identities;
    for (const auto& raw : document["packages"]) {
        auto package = core::take(Package::parse(raw));
        require(identities.insert(package.candidate().artifact()).second,
                "duplicate catalog artifact");
        result.push_back(std::move(package));
    }
    return result;
}

package::Selection candidates(const Selection& selected) {
    package::Selection result;
    for (const auto& [name, package] : selected) {
        result.emplace(name, package.candidate());
    }
    return result;
}
Selection resolve_impl(const std::vector<Package>& packages, const std::set<std::string>& roots,
                       const Selection& installed, resolver::Preference preference,
                       const package::Target& target, package::PrereleasePolicy prereleases) {
    std::vector<package::Candidate> inputs;
    inputs.reserve(packages.size());
    for (const auto& package : packages) {
        inputs.push_back(package.candidate());
    }
    const auto chosen = aslice::core::take(
        resolver::solve(inputs, roots, candidates(installed), preference, target, prereleases));
    Selection result;
    for (const auto& [name, candidate] : chosen) {
        const auto identity = candidate.artifact();
        const auto found =
            std::find_if(packages.begin(), packages.end(), [&identity](const auto& package) {
                return package.candidate().artifact() == identity;
            });
        require(found != packages.end(), "resolver returned unknown candidate");
        result.emplace(name, *found);
    }
    return result;
}

core::Result<Generation> Generation::parse(const core::Json& document,
                                           const std::string& expected_id) {
    try {
        require(document.at("format") == format && document.at("generation") == expected_id,
                "invalid generation state");
        require(!expected_id.empty() &&
                    expected_id.find_first_not_of("0123456789") == std::string::npos,
                "invalid generation ID");
        auto selected = aslice::core::take(selection(document.at("selected")));
        auto roots = aslice::core::take(requested(document));
        for (const auto& root : roots) {
            require(selected.contains(root), "requested package is absent from generation");
        }
        const auto parent = document.at("parent").get<std::string>();
        require(parent.find_first_not_of("0123456789") == std::string::npos,
                "invalid parent generation ID");
        return Generation(expected_id, parent, std::move(selected), std::move(roots));
    } catch (const std::exception& error) {
        return tl::unexpected(core::Failure{"invalid_generation", error.what()});
    }
}
core::Json generation_document(const std::string& id, const std::string& parent,
                               const Selection& selected, const std::set<std::string>& roots) {
    return {{"format", format},
            {"generation", id},
            {"parent", parent},
            {"requested", roots},
            {"selected", serialize(selected)}};
}

core::Result<Selection> selection(const Json& value) {
    return core::capture([&] {
        return selection_impl(value);
    });
}

core::Result<std::set<std::string>> requested(const Json& document) {
    return core::capture([&] {
        return requested_impl(document);
    });
}

core::Result<std::vector<Package>> catalog(const Json& document) {
    return core::capture([&] {
        return catalog_impl(document);
    });
}

core::Result<Selection> resolve(const std::vector<Package>& packages,
                                const std::set<std::string>& roots, const Selection& installed,
                                resolver::Preference preference, const package::Target& target,
                                package::PrereleasePolicy prereleases) {
    return core::capture([&] {
        return resolve_impl(packages, roots, installed, preference, target, prereleases);
    });
}
} // namespace aslice::adapters::fixture
