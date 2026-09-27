#ifndef ASLICE_STORE_FIXTURE_STORE_HPP
#define ASLICE_STORE_FIXTURE_STORE_HPP
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"

namespace aslice::store {
core::Result<void> verify_store(platform::FileSystem& filesystem, const platform::TargetPath& root,
                                const adapters::fixture::Package& package);
core::Result<void> import_package(platform::FileSystem& filesystem,
                                  const platform::TargetPath& root,
                                  const adapters::fixture::Package& package);

} // namespace aslice::store

#endif // ASLICE_STORE_FIXTURE_STORE_HPP
