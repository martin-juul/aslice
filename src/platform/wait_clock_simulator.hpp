#ifndef ASLICE_PLATFORM_WAIT_CLOCK_SIMULATOR_HPP
#define ASLICE_PLATFORM_WAIT_CLOCK_SIMULATOR_HPP
#include "platform/simulator.hpp"
#include "platform/wait_clock.hpp"
#include <stop_token>

namespace aslice::platform {
class SimulatorWaitClock final : public WaitClock {
  public:
    explicit SimulatorWaitClock(Simulator& connection) : connection_(connection) {}
    Milliseconds now() override;
    void wait(Milliseconds duration, std::stop_token cancellation) override;

  private:
    Simulator& connection_;
};
} // namespace aslice::platform
#endif
