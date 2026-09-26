#include "package/candidate.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/version.hpp"
#include "tl/expected.hpp"
#include <algorithm>
#include <array>
#include <filesystem>
#include <set>
#include <string>
#include <utility>
namespace aslice::package {
using core::require;
bool name_valid(const std::string& name) {
    return !name.empty() && name.size() <= 64 && name.front() != '-' &&
           name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-") == std::string::npos;
}
std::string key_impl(std::string value) {
    if (value.find(':') == std::string::npos) {
        value = "core:" + value;
    }
    const auto colon = value.find(':');
    require(name_valid(value.substr(0, colon)) && name_valid(value.substr(colon + 1)),
            "invalid package name: " + value);
    return value;
}
Version version_impl(const std::string& value) {
    return aslice::core::take(Version::parse(value));
}
bool satisfies_impl(const std::string& value, const std::string& constraint) {
    return aslice::core::take(Constraint::parse(constraint)).matches(core::take(version(value)));
}
int os_rank_impl(const std::string& value) {
    const std::array<std::string, 7> supported{"10.11", "10.12", "10.13", "10.14",
                                               "10.15", "11",    "12"};
    auto at = std::find(supported.begin(), supported.end(), value);
    require(at != supported.end(), "target OS must be 10.11 through 12");
    return static_cast<int>(at - supported.begin());
}
int flavor_rank_impl(const std::string& value) {
    require(value == "v1" || value == "v2" || value == "v3", "flavor must be v1, v2, or v3");
    return value.back() - '0';
}

core::Result<Target> Target::create(std::string os, std::string flavor) {
    try {
        core::take(os_rank(os));
        core::take(flavor_rank(flavor));
        return Target(std::move(os), std::move(flavor));
    } catch (const core::Error& error) {
        return tl::unexpected(core::Failure{"invalid_target", error.what()});
    }
}
core::Result<Candidate> Candidate::create(std::string name, std::string release, Target target,
                                          Dependencies dependencies, std::set<std::string> paths,
                                          std::string artifact) {
    try {
        name = core::take(key(std::move(name)));
        core::take(version(release));
        require(dependencies.size() <= 64, "invalid dependency map");
        for (const auto& [dependency, constraint] : dependencies) {
            require(core::take(key(dependency)) == dependency, "unnormalized dependency");
            (void)constraint;
        }
        require(artifact.size() == 64 &&
                    artifact.find_first_not_of("0123456789abcdef") == std::string::npos,
                "invalid artifact identity");
        require(paths.size() <= 128, "invalid inventory");
        for (const auto& path : paths) {
            const core::fs::path parsed(path);
            require(!path.empty() && parsed.is_relative() &&
                        parsed.lexically_normal().generic_string() == path,
                    "invalid inventory path");
            for (const auto& part : parsed) {
                require(part != "." && part != "..", "unsafe inventory path");
            }
        }
        return Candidate(core::take(Identity::parse(std::move(name))), std::move(release),
                         std::move(target), std::move(dependencies), std::move(paths),
                         std::move(artifact));
    } catch (const core::Error& error) {
        return tl::unexpected(core::Failure{"invalid_candidate", error.what()});
    }
}

core::Result<Identity> Identity::parse(std::string name) {
    return core::capture([&] {
        return Identity(core::take(key(std::move(name))));
    });
}

core::Result<std::string> key(std::string value) {
    return core::capture([&] {
        return key_impl(std::move(value));
    });
}

core::Result<Version> version(const std::string& value) {
    return core::capture([&] {
        return version_impl(value);
    });
}

core::Result<bool> satisfies(const std::string& value, const std::string& constraint) {
    return core::capture([&] {
        return satisfies_impl(value, constraint);
    });
}

core::Result<int> os_rank(const std::string& value) {
    return core::capture([&] {
        return os_rank_impl(value);
    });
}

core::Result<int> flavor_rank(const std::string& value) {
    return core::capture([&] {
        return flavor_rank_impl(value);
    });
}
} // namespace aslice::package
