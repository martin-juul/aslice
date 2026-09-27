#include "platform/wait_clock.hpp"
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <stop_token>

namespace aslice::platform {
Milliseconds NativeWaitClock::now() {
    return std::chrono::duration_cast<Milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch());
}
void NativeWaitClock::wait(Milliseconds duration, std::stop_token cancellation) {
    std::mutex mutex;
    std::unique_lock lock{mutex};
    std::condition_variable_any condition;
    condition.wait_for(lock, cancellation, duration, [] {
        return false;
    });
}
} // namespace aslice::platform
