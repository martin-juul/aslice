#include "platform/wait_clock_simulator.hpp"
#include "core/support.hpp"
#include "platform/wait_clock.hpp"
#include <cstdint>
#include <stop_token>
#include <string>

namespace aslice::platform {
namespace {
core::Json checked(core::Json response) {
    const auto& failure = response.at("failure");
    if (!failure.is_null()) {
        throw core::Error(failure.at("message").get<std::string>(),
                          failure.at("code").get<std::string>());
    }
    return response.at("result");
}
} // namespace
Milliseconds SimulatorWaitClock::now() {
    return Milliseconds{checked(core::take(connection_.request("clock", "observe")))
                            .at("monotonic_ms")
                            .get<std::int64_t>()};
}
void SimulatorWaitClock::wait(Milliseconds duration, std::stop_token cancellation) {
    if (!cancellation.stop_requested()) {
        checked(
            core::take(connection_.request("clock", "wait", {{"milliseconds", duration.count()}})));
    }
}
} // namespace aslice::platform
