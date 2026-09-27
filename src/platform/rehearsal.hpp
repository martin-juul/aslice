#ifndef ASLICE_PLATFORM_REHEARSAL_HPP
#define ASLICE_PLATFORM_REHEARSAL_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include <memory>
#include <string>

namespace aslice::platform {
// Linked only into rehearsal binaries. No environment selector exists in aslice.
class Rehearsal {
  public:
    explicit Rehearsal(const HostPath& session);
    ~Rehearsal();
    Rehearsal(const Rehearsal&) = delete;
    Rehearsal& operator=(const Rehearsal&) = delete;
    core::Result<core::Json> request(const std::string& capability, const std::string& operation,
                                     const core::Json& arguments = core::Json::object(),
                                     const core::Json& preconditions = core::Json::object());
    core::Result<core::Json> filesystem(const std::string& operation, const TargetPath& path,
                                        core::Json arguments = core::Json::object());

  private:
    struct Impl;
    std::unique_ptr<Impl> implementation_;
};
} // namespace aslice::platform
#endif
