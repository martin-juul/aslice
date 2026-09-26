#ifndef ASLICE_PACKAGE_SLICE_HPP
#define ASLICE_PACKAGE_SLICE_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/manifest.hpp"
#include <filesystem>
#include <string>
namespace aslice::package {
// Bounded unsigned local inspection/packing; never authorizes installation.
core::Result<core::Json> inspect_slice(const core::fs::path& file);
core::Result<std::string> pack_slice(const Manifest& manifest, const core::fs::path& payload);
} // namespace aslice::package

#endif // ASLICE_PACKAGE_SLICE_HPP
