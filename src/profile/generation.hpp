#ifndef ASLICE_PROFILE_GENERATION_HPP
#define ASLICE_PROFILE_GENERATION_HPP
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include <filesystem>
#include <set>
#include <string>

namespace aslice::profile {
core::Result<void> check_prefix(const core::fs::path& root);
core::Result<std::string> current_id(const core::fs::path& root);
core::Result<adapters::fixture::Generation> state(const core::fs::path& root,
                                                  const std::string& generation);
core::Result<void> switch_to(const core::fs::path& root, const std::string& generation);
core::Result<std::string> commit(const core::fs::path& root,
                                 const adapters::fixture::Selection& selected,
                                 const std::set<std::string>& roots, const std::string& parent);
core::Result<void> verify_generation(const core::fs::path& root, const std::string& id,
                                     const adapters::fixture::Selection& selected);

} // namespace aslice::profile

#endif // ASLICE_PROFILE_GENERATION_HPP
