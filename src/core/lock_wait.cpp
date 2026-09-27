#include "core/lock_wait.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/wait_clock.hpp"
#include <algorithm>
#include <charconv>
#include <cstdint>
#include <limits>
#include <stop_token>
#include <string_view>
#include <system_error>
#include <utility>

namespace aslice::core {
using platform::Milliseconds;
Result<Milliseconds> parse_lock_timeout(std::string_view text) {
    return capture([&] {
        std::int64_t multiplier = 0;
        if (text.ends_with("ms")) {
            multiplier = 1;
            text.remove_suffix(2);
        } else if (text.ends_with('s')) {
            multiplier = 1000;
            text.remove_suffix(1);
        } else if (text.ends_with('m')) {
            multiplier = 60000;
            text.remove_suffix(1);
        }
        require(multiplier != 0 && !text.empty() &&
                    std::all_of(text.begin(), text.end(),
                                [](char character) {
                                    return character >= '0' && character <= '9';
                                }),
                "lock timeout requires a nonnegative integer followed by ms, s or m");
        std::int64_t number = 0;
        const auto result = std::from_chars(text.data(), text.data() + text.size(), number);
        require(result.ec == std::errc{} && result.ptr == text.data() + text.size() &&
                    number <= std::numeric_limits<std::int64_t>::max() / multiplier,
                "lock timeout exceeds supported duration");
        return Milliseconds{number * multiplier};
    });
}
LockWait::LockWait(platform::WaitClock& clock, bool authorized, Milliseconds allowance,
                   std::stop_token cancellation, Progress progress)
    : clock_(clock), authorized_(authorized), allowance_(allowance),
      cancellation_(std::move(cancellation)), progress_(std::move(progress)) {
    require(allowance.count() >= 0, "negative lock-wait allowance");
}
LockWait::Budget& LockWait::budget() {
    return recovering_ ? recovery_ : foreground_;
}
const LockWait::Budget& LockWait::budget() const {
    return recovering_ ? recovery_ : foreground_;
}
Milliseconds LockWait::limit() const {
    return recovering_ ? Milliseconds{30000} : allowance_;
}
bool LockWait::cancelled() const {
    return !recovering_ && cancellation_.stop_requested();
}
Milliseconds LockWait::elapsed() const {
    return budget().used;
}
Milliseconds LockWait::remaining() const {
    return budget().used >= limit() ? Milliseconds{0} : limit() - budget().used;
}
void LockWait::begin_recovery() {
    recovering_ = true;
}
WaitResult LockWait::after_contention(const WaitContext& context) {
    require(!clock_failed_, "lock-wait clock outcome is unresolved");
    if (cancelled()) {
        return WaitResult::cancelled;
    }
    if ((!authorized_ && !recovering_) || remaining().count() == 0) {
        return WaitResult::exhausted;
    }
    auto& current = budget();
    const auto duration = std::min(current.backoff, remaining());
    // If observation or wait fails, further waits cannot safely reuse an
    // allowance whose consumption is unknown. Immediate lock attempts remain
    // the caller's choice; recovery never renews an uncertain clock budget.
    clock_failed_ = true;
    const auto before = clock_.now();
    require(before.count() >= 0, "invalid monotonic clock");
    clock_.wait(duration, recovering_ ? std::stop_token{} : cancellation_);
    const auto after = clock_.now();
    require(after >= before, "monotonic clock moved backward");
    const auto waited = after - before;
    clock_failed_ = false;
    // Spurious wakeups and scheduler overshoot use measured elapsed time, never
    // requested sleep time. Useful work and progress rendering are not charged.
    current.used += std::min(waited, Milliseconds::max() - current.used);
    current.backoff = std::min(current.backoff * 2, Milliseconds{250});
    if (progress_ && current.used >= current.next_report) {
        auto observed = context;
        if (observed.owner.empty()) {
            observed.owner = "unknown";
        }
        progress_(observed, current.used, recovering_);
        current.next_report = current.used > Milliseconds::max() - Milliseconds{5000}
                                  ? Milliseconds::max()
                                  : current.used + Milliseconds{5000};
    }
    if (cancelled()) {
        return WaitResult::cancelled;
    }
    return remaining().count() == 0 ? WaitResult::exhausted : WaitResult::retry;
}
} // namespace aslice::core
