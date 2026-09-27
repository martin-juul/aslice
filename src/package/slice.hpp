#ifndef ASLICE_PACKAGE_SLICE_HPP
#define ASLICE_PACKAGE_SLICE_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/manifest.hpp"
#include "platform/target_filesystem.hpp"
#include <string>
namespace aslice::package {
// Bounded unsigned local inspection/packing; never authorizes installation.
core::Result<core::Json> inspect_slice(platform::FileSystem& filesystem,
                                       const platform::TargetPath& file);
core::Result<std::string> pack_slice(platform::FileSystem& filesystem, const Manifest& manifest,
                                     const platform::TargetPath& payload);
} // namespace aslice::package

#endif // ASLICE_PACKAGE_SLICE_HPP
