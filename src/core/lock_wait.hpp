#ifndef ASLICE_CORE_LOCK_WAIT_HPP
#define ASLICE_CORE_LOCK_WAIT_HPP
#include "core/result.hpp"
#include "platform/wait_clock.hpp"
#include <cstdint>
#include <functional>
#include <stop_token>
#include <string>
#include <string_view>

namespace aslice::core {
Result<platform::Milliseconds> parse_lock_timeout(std::string_view text);
struct WaitContext {
    std::string role;
    std::string operation;
    // Only an independently established owner identity belongs here, never a PID guess.
    std::string owner = "unknown";
};
enum class WaitResult : std::uint8_t { retry, exhausted, cancelled };
// One instance per operation, shared by every owner lock and SQL BUSY path.
// It never retries effects, releases ownership, decides recovery, or assigns CLI exit codes.
class LockWait {
  public:
    using Progress = std::function<void(const WaitContext&, platform::Milliseconds, bool)>;
    LockWait(platform::WaitClock& clock, bool authorized,
             platform::Milliseconds allowance = platform::Milliseconds{30000},
             std::stop_token cancellation = {}, Progress progress = {});
    LockWait(const LockWait&) = delete;
    LockWait& operator=(const LockWait&) = delete;
    bool cancelled() const;
    WaitResult after_contention(const WaitContext& context);
    // Idempotent: neither retries nor repeated cancellation renew this allowance.
    // The recovery controller calls this only after establishing durable phase.
    void begin_recovery();
    platform::Milliseconds elapsed() const;
    platform::Milliseconds remaining() const;

  private:
    struct Budget {
        platform::Milliseconds used{0};
        platform::Milliseconds backoff{10};
        platform::Milliseconds next_report{1000};
    };
    platform::WaitClock& clock_;
    bool authorized_;
    platform::Milliseconds allowance_;
    std::stop_token cancellation_;
    Progress progress_;
    Budget foreground_;
    Budget recovery_;
    bool recovering_ = false;
    bool clock_failed_ = false;
    Budget& budget();
    const Budget& budget() const;
    platform::Milliseconds limit() const;
};
} // namespace aslice::core
#endif
