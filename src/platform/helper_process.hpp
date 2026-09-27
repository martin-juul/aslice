#ifndef ASLICE_PLATFORM_HELPER_PROCESS_HPP
#define ASLICE_PLATFORM_HELPER_PROCESS_HPP
#include "core/support.hpp"
#include "platform/paths.hpp"
#include <chrono>
#include <optional>
#include <stop_token>

namespace aslice::platform {
// Development-host adapter for one read-only inspection. The executable must be
// the caller-selected manager binary. This does not establish its code identity,
// sandbox it, or authorize any external effects.
core::Result<core::Json>
inspect_in_helper(const HostPath& executable, const core::Json& manifest,
                  std::chrono::milliseconds timeout = std::chrono::seconds{30},
                  std::stop_token stop = {});
// Private reexecution entry point, outside the public command registry.
// Returns nullopt for ordinary CLI invocations.
std::optional<int> inspection_helper_entry(int argc, char** argv);
} // namespace aslice::platform
#endif
