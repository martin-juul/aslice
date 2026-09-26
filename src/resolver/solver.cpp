#include "resolver/solver.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "package/version.hpp"
#include <algorithm>
#include <cstddef>
#include <functional>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace aslice::resolver {
constexpr std::size_t search_step_limit = 10000;
constexpr std::size_t closure_limit = 128;
namespace fs = std::filesystem;
using core::require;
using package::Candidate;
using package::Constraint;
using package::flavor_rank;
using package::os_rank;
using package::Selection;
using package::Target;
using package::version;
bool consistent(const Selection& selected) {
    std::set<std::string> active;
    std::set<std::string> done;
    std::function<bool(const std::string&)> visit = [&](const std::string& name) {
        if (active.contains(name)) {
            return false;
        }
        if (done.contains(name)) {
            return true;
        }
        active.insert(name);
        for (const auto& [dependency, constraint] : selected.at(name).dependencies()) {
            if (!selected.contains(dependency) ||
                !constraint.matches(core::take(version(selected.at(dependency).release())),
                                    package::PrereleasePolicy::allow) ||
                !visit(dependency)) {
                return false;
            }
        }
        active.erase(name);
        done.insert(name);
        return true;
    };
    for (const auto& [name, package] : selected) {
        (void)package;
        if (!visit(name)) {
            return false;
        }
    }
    return true;
}
void collisions_impl(const Selection& selected) {
    std::set<std::string> paths;
    for (const auto& [name, package] : selected) {
        for (const auto& path : package.paths()) {
            std::string lower = path;
            std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
                return c >= 'A' && c <= 'Z' ? static_cast<char>(c + 32) : static_cast<char>(c);
            });
            require(
                paths.insert(lower).second,
                std::string("profile path collision: ").append(path).append(" from ").append(name));
        }
    }
    for (const auto& path : paths) {
        for (auto p = fs::path(path).parent_path(); !p.empty(); p = p.parent_path()) {
            require(!paths.contains(p.generic_string()),
                    "profile file/directory collision: " + path);
        }
    }
}
Selection solve_impl(const std::vector<Candidate>& packages, const std::set<std::string>& roots,
                     const Selection& installed, Preference preference, const Target& target,
                     package::PrereleasePolicy prereleases) {
    std::map<std::string, std::vector<Candidate>> candidates;
    for (const auto& package : packages) {
        if (core::take(os_rank(package.target().os())) <= core::take(os_rank(target.os())) &&
            core::take(flavor_rank(package.target().flavor())) <=
                core::take(flavor_rank(target.flavor()))) {
            candidates[package.name()].push_back(package);
        }
    }
    for (auto& [name, options] : candidates) {
        const auto candidate_name = name;
        std::sort(options.begin(), options.end(), [&](const Candidate& a, const Candidate& b) {
            if (preference == Preference::installed && installed.contains(candidate_name)) {
                const auto& previous = installed.at(candidate_name).artifact();
                if ((a.artifact() == previous) != (b.artifact() == previous)) {
                    return a.artifact() == previous;
                }
            }
            if (core::take(version(a.release())) != core::take(version(b.release()))) {
                return core::take(version(a.release())) > core::take(version(b.release()));
            }
            if (a.target().flavor() != b.target().flavor()) {
                return a.target().flavor() > b.target().flavor();
            }
            return a.artifact() < b.artifact();
        });
    }
    std::size_t attempts = 0;
    std::string conflict;
    const auto matches = [&](const std::string& release,
                             const std::vector<Constraint>& constraints) {
        const auto value = core::take(version(release));
        bool admitted = !value.prerelease() || prereleases == package::PrereleasePolicy::allow;
        bool matched = true;
        for (const auto& constraint : constraints) {
            admitted |= constraint.matches(value);
            matched &= constraint.matches(value, package::PrereleasePolicy::allow);
        }
        return admitted && matched;
    };
    std::function<bool(Selection&)> search = [&](Selection& chosen) {
        require(++attempts <= search_step_limit, "prototype solver exceeded 10,000 search steps");
        std::map<std::string, std::vector<Constraint>> requirements;
        for (const auto& root : roots) {
            requirements[root].push_back(core::take(Constraint::parse("*")));
        }
        for (const auto& [name, package] : chosen) {
            (void)name;
            for (const auto& [dependency, constraint] : package.dependencies()) {
                requirements[dependency].push_back(constraint);
            }
        }
        require(requirements.size() <= closure_limit, "prototype closure exceeds 128 packages");
        for (const auto& [name, constraints] : requirements) {
            if (!chosen.contains(name)) {
                continue;
            }
            if (!matches(chosen.at(name).release(), constraints)) {
                conflict = "incompatible constraints for " + name;
                return false;
            }
        }
        for (const auto& [name, constraints] : requirements) {
            if (chosen.contains(name)) {
                continue;
            }
            conflict = "no compatible candidate for " + name;
            for (const auto& candidate : candidates[name]) {
                if (!matches(candidate.release(), constraints)) {
                    continue;
                }
                auto next = chosen;
                next.emplace(name, candidate);
                if (search(next)) {
                    chosen = std::move(next);
                    return true;
                }
            }
            return false;
        }
        if (!consistent(chosen)) {
            conflict = "dependency cycle";
            return false;
        }
        return true;
    };
    Selection result;
    const bool found = search(result);
    require(found, "resolution refused: " + conflict);
    aslice::core::take(collisions(result));
    return result;
}

core::Result<Selection> solve(const std::vector<Candidate>& packages,
                              const std::set<std::string>& roots, const Selection& installed,
                              Preference preference, const Target& target,
                              package::PrereleasePolicy prereleases) {
    return core::capture([&] {
        return solve_impl(packages, roots, installed, preference, target, prereleases);
    });
}

core::Result<void> collisions(const Selection& selected) {
    return core::capture([&] {
        return collisions_impl(selected);
    });
}
} // namespace aslice::resolver
