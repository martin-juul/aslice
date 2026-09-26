#ifndef ASLICE_STORE_FIXTURE_STORE_HPP
#define ASLICE_STORE_FIXTURE_STORE_HPP
#include "adapters/fixture.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include <filesystem>

namespace aslice::store {
core::Result<void> verify_store(const core::fs::path& root,
                                const adapters::fixture::Package& package);
core::Result<void> import_package(const core::fs::path& root,
                                  const adapters::fixture::Package& package);

} // namespace aslice::store

#endif // ASLICE_STORE_FIXTURE_STORE_HPP
