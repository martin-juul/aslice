#ifndef ASLICE_HELPER_PROTOCOL_HPP
#define ASLICE_HELPER_PROTOCOL_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include <cstddef>
#include <cstdint>
#include <functional>
#include <istream>
#include <mutex>
#include <optional>
#include <set>
#include <string>

namespace aslice::helper {
inline constexpr std::size_t maximum_frame = 1024 * 1024;
// Supplied by a trusted launcher/platform adapter, never deserialized from an
// incoming helper request. This protocol layer does not authenticate OS peers.
struct Grant {
    std::string caller;
    std::string role;
    std::string instance_id;
    std::string operation_id;
    std::string session_id;
    std::string plan_digest;
    std::set<std::string> capabilities;
};
struct Request {
    std::uint64_t sequence;
    std::string command;
    core::Json arguments;
};
struct Outcome {
    core::Json observations = core::Json::array();
    core::Json effects = core::Json::array();
    core::Json receipt = nullptr;
    std::optional<core::Failure> failure;
};
// Framing is transport-independent. Empty optional means clean EOF between
// messages; incomplete frames are errors, never successful empty requests.
core::Result<std::optional<core::Json>> read_frame(std::istream& input);
core::Result<std::string> encode_frame(const core::Json& message);

class Session {
  public:
    explicit Session(const Grant& grant);
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
    const core::Json& binding() const {
        return binding_;
    }
    using Handler = std::function<void(const Request&, Outcome&)>;
    // Serializes admission/execution for this channel. Handlers must not reenter
    // the same Session. A sequence is consumed before calling the handler, even
    // when execution fails or the response is lost. This is not a durable journal.
    // helper_outcome_unknown means admission occurred but no valid bounded reply
    // is available; helper_replay requires durable outcome lookup, not reexecution.
    core::Result<core::Json> execute(const core::Json& message, const Handler& handler);
    core::Result<Outcome> verify_response(const core::Json& message, std::uint64_t sequence) const;

  private:
    core::Json binding_;
    std::set<std::string> capabilities_;
    std::uint64_t sequence_ = 0;
    std::mutex mutex_;
};
} // namespace aslice::helper
#endif
