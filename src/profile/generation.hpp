#ifndef ASLICE_PROFILE_GENERATION_HPP
#define ASLICE_PROFILE_GENERATION_HPP
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <set>
#include <string>

namespace aslice::profile {
core::Result<void> check_prefix(platform::FileSystem& filesystem, const platform::TargetPath& root);
core::Result<std::string> current_id(platform::FileSystem& filesystem,
                                     const platform::TargetPath& root);
core::Result<adapters::fixture::Generation> state(platform::FileSystem& filesystem,
                                                  const platform::TargetPath& root,
                                                  const std::string& generation);
core::Result<void> switch_to(platform::FileSystem& filesystem, const platform::TargetPath& root,
                             const std::string& generation);
core::Result<std::string> commit(platform::FileSystem& filesystem, const platform::TargetPath& root,
                                 const adapters::fixture::Selection& selected,
                                 const std::set<std::string>& roots, const std::string& parent);
core::Result<void> verify_generation(platform::FileSystem& filesystem,
                                     const platform::TargetPath& root, const std::string& id,
                                     const adapters::fixture::Selection& selected);

} // namespace aslice::profile

#endif // ASLICE_PROFILE_GENERATION_HPP
