#ifndef ASLICE_RESOLVER_SOLVER_HPP
#define ASLICE_RESOLVER_SOLVER_HPP
#include "core/result.hpp"
#include "package/candidate.hpp"
#include "package/version.hpp"
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace aslice::resolver {
enum class Preference : std::uint8_t { installed, newest };
bool consistent(const package::Selection& selected);
core::Result<void> collisions(const package::Selection& selected);
core::Result<package::Selection>
solve(const std::vector<package::Candidate>& packages, const std::set<std::string>& roots,
      const package::Selection& installed, Preference preference, const package::Target& target,
      package::PrereleasePolicy prereleases = package::PrereleasePolicy::normal);

} // namespace aslice::resolver

#endif // ASLICE_RESOLVER_SOLVER_HPP
