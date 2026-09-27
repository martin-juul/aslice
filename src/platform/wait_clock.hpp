#ifndef ASLICE_PLATFORM_WAIT_CLOCK_HPP
#define ASLICE_PLATFORM_WAIT_CLOCK_HPP
#include <chrono>
#include <stop_token>

namespace aslice::platform {
using Milliseconds = std::chrono::milliseconds;
class WaitClock {
  public:
    virtual ~WaitClock() = default;
    virtual Milliseconds now() = 0;
    virtual void wait(Milliseconds duration, std::stop_token cancellation) = 0;
};
class NativeWaitClock final : public WaitClock {
  public:
    Milliseconds now() override;
    void wait(Milliseconds duration, std::stop_token cancellation) override;
};
} // namespace aslice::platform
#endif
