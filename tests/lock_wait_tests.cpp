#include "core/lock_wait.hpp"
#include "core/support.hpp"
#include "platform/wait_clock.hpp"
#include <chrono>
#include <cstddef>
#include <exception>
#include <iostream>
#include <stop_token>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

namespace {
using aslice::core::LockWait;
using aslice::core::require;
using aslice::core::WaitResult;
using aslice::platform::Milliseconds;
class Clock final : public aslice::platform::WaitClock {
  public:
    Milliseconds time{0};
    Milliseconds overshoot{0};
    std::vector<Milliseconds> sleeps;
    std::stop_source* cancel = nullptr;
    Milliseconds now() override {
        return time;
    }
    void wait(Milliseconds duration, std::stop_token cancellation) override {
        sleeps.push_back(duration);
        if (!cancellation.stop_requested()) {
            time += duration + overshoot;
        }
        if (cancel != nullptr) {
            cancel->request_stop();
        }
    }
};
void parsing() {
    using aslice::core::parse_lock_timeout;
    for (const auto* invalid :
         {"", "30", "1h", "-1s", "+1s", "1.5s", " 1s", "1s ", "1MS", "s", "1e3ms",
          "9223372036854775808ms", "9223372036854776s", "153722867280913m"}) {
        require(!parse_lock_timeout(invalid), std::string("accepted invalid duration: ") + invalid);
    }
    require(aslice::core::take(parse_lock_timeout("0s")) == Milliseconds{0}, "zero timeout");
    require(aslice::core::take(parse_lock_timeout("001ms")) == Milliseconds{1}, "leading zeros");
    require(aslice::core::take(parse_lock_timeout("30s")) == Milliseconds{30000}, "seconds");
    require(aslice::core::take(parse_lock_timeout("2m")) == Milliseconds{120000}, "minutes");
    require(aslice::core::take(parse_lock_timeout("9223372036854775807ms")) == Milliseconds::max(),
            "maximum timeout");
}
void budgets() {
    Clock clock;
    const aslice::core::WaitContext prefix{"client-state", "install", "owner-1"};
    const aslice::core::WaitContext sql{"system-state", "BEGIN IMMEDIATE", "owner-2"};
    LockWait denied{clock, false, Milliseconds{30000}};
    require(denied.after_contention(prefix) == WaitResult::exhausted && clock.sleeps.empty(),
            "timeout configuration authorized waiting");
    LockWait zero{clock, true, Milliseconds{0}};
    require(zero.after_contention(prefix) == WaitResult::exhausted && clock.sleeps.empty(),
            "zero timeout slept");
    LockWait waiting{clock, true, Milliseconds{65}};
    require(waiting.after_contention(prefix) == WaitResult::retry, "initial retry");
    clock.time += Milliseconds{100000}; // Useful work between lock layers.
    require(waiting.after_contention(sql) == WaitResult::retry, "cross-layer retry");
    require(waiting.after_contention(prefix) == WaitResult::exhausted, "clipped budget");
    require(clock.sleeps ==
                std::vector<Milliseconds>{Milliseconds{10}, Milliseconds{20}, Milliseconds{35}},
            "backoff or cross-layer accounting");
    require(waiting.elapsed() == Milliseconds{65} && waiting.remaining() == Milliseconds{0},
            "useful work charged to allowance");
    require(waiting.after_contention(sql) == WaitResult::exhausted && clock.sleeps.size() == 3,
            "exhausted budget renewed");
    Clock late;
    late.overshoot = Milliseconds{1000};
    LockWait overshot{late, true, Milliseconds{200}};
    require(overshot.after_contention(prefix) == WaitResult::exhausted &&
                overshot.remaining().count() == 0 && overshot.elapsed() == Milliseconds{1010},
            "scheduler overshoot was not charged safely");
}
void cancellation_and_recovery() {
    Clock clock;
    std::stop_source cancellation;
    clock.cancel = &cancellation;
    LockWait waiting{clock, true, Milliseconds{10}, cancellation.get_token()};
    require(waiting.after_contention({}) == WaitResult::cancelled, "cancellation during wait");
    require(waiting.after_contention({}) == WaitResult::cancelled && clock.sleeps.size() == 1,
            "cancelled operation waited again");
    waiting.begin_recovery();
    require(!waiting.cancelled() && waiting.remaining() == Milliseconds{30000},
            "recovery allowance");
    require(waiting.after_contention({}) == WaitResult::retry,
            "foreground cancellation abandoned recovery");
    waiting.begin_recovery();
    require(waiting.remaining() == Milliseconds{29990}, "recovery budget reset");
    std::size_t attempts = 0;
    while (waiting.after_contention({}) == WaitResult::retry) {
        require(++attempts < 130, "unbounded recovery waits");
        waiting.begin_recovery();
        cancellation.request_stop();
    }
    require(waiting.elapsed() == Milliseconds{30000}, "recovery did not use its single budget");
    for (const auto delay : clock.sleeps) {
        require(delay.count() > 0 && delay <= Milliseconds{250}, "uncapped backoff");
    }
}
void progress_and_clock_failure() {
    Clock clock;
    std::vector<Milliseconds> progress;
    LockWait waiting{
        clock,
        true,
        Milliseconds{7000},
        {},
        [&](const aslice::core::WaitContext& context, Milliseconds elapsed, bool recovery) {
            require(context.owner == "unknown" && context.role == "publisher" &&
                        context.operation == "reserve" && !recovery,
                    "progress identity");
            progress.push_back(elapsed);
            clock.time += Milliseconds{10000}; // Rendering is not lock waiting.
        }};
    while (waiting.after_contention({"publisher", "reserve", ""}) == WaitResult::retry) {
    }
    require(progress.size() == 2 && progress[0] >= Milliseconds{1000} &&
                progress[0] < Milliseconds{1250} &&
                progress[1] - progress[0] >= Milliseconds{5000} &&
                waiting.elapsed() == Milliseconds{7000},
            "progress cadence or accounting");
    Clock broken;
    broken.time = Milliseconds{1000};
    broken.overshoot = Milliseconds{-100};
    LockWait invalid{broken, true};
    require(!aslice::core::capture([&] {
        return invalid.after_contention({});
    }),
            "backward clock accepted");
    broken.overshoot = Milliseconds{0};
    invalid.begin_recovery();
    require(!aslice::core::capture([&] {
        return invalid.after_contention({});
    }) && broken.sleeps.size() == 1,
            "uncertain clock budget reused during recovery");
}
void native_cancellation() {
    aslice::platform::NativeWaitClock clock;
    std::stop_source cancellation;
    std::jthread cancel{[&] {
        std::this_thread::sleep_for(std::chrono::milliseconds{20});
        cancellation.request_stop();
    }};
    const auto before = clock.now();
    clock.wait(Milliseconds{10000}, cancellation.get_token());
    require(cancellation.stop_requested() && clock.now() - before < Milliseconds{2000},
            "native wait did not wake for cancellation");
}
} // namespace
int main() {
    static_assert(!std::is_copy_constructible_v<LockWait>);
    try {
        parsing();
        budgets();
        cancellation_and_recovery();
        progress_and_clock_failure();
        native_cancellation();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
