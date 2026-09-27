#ifndef ASLICE_HELPER_INSPECTION_HPP
#define ASLICE_HELPER_INSPECTION_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include <string>

namespace aslice::helper {
// One read-only request per launched inspection helper. Caller identity comes
// from its platform channel; incoming correlation IDs confer no authority.
core::Result<core::Json> inspect_message(const core::Json& request,
                                         const std::string& authenticated_caller);
} // namespace aslice::helper
#endif
