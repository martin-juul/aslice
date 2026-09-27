#ifndef ASLICE_PLATFORM_SIMULATOR_HPP
#define ASLICE_PLATFORM_SIMULATOR_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include <memory>
#include <string>

namespace aslice::platform {
// Linked only into simulator binaries. No environment selector exists in aslice.
class Simulator {
  public:
    explicit Simulator(const HostPath& session);
    ~Simulator();
    Simulator(const Simulator&) = delete;
    Simulator& operator=(const Simulator&) = delete;
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
