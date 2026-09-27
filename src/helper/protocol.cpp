#include "helper/protocol.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <ios>
#include <istream>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace aslice::helper {
namespace {
constexpr std::uint64_t maximum_sequence = 9007199254740991ULL;
void require(bool condition, const std::string& message) {
    if (!condition) {
        throw core::Error(message, "helper_protocol");
    }
}
void fields(const core::Json& object, const std::set<std::string>& expected) {
    core::take(core::fields(object, expected));
    require(object.size() == expected.size(), "missing helper message fields");
}
bool hex(std::string_view value, std::size_t length) {
    return value.size() == length && std::all_of(value.begin(), value.end(), [](char character) {
               return (character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f');
           });
}
bool bounded_text(const std::string& value, std::size_t maximum) {
    return !value.empty() && value.size() <= maximum &&
           std::all_of(value.begin(), value.end(), [](unsigned char character) {
               return character >= 0x20 && character != 0x7f;
           });
}
core::Json binding(const Grant& grant) {
    // Only ordinary role vocabularies are defined here. The protected system
    // helper needs its separate installation and authorization implementation.
    static const std::map<std::string, std::set<std::string>> vocabulary{
        {"fetch", {"fetch.input"}},
        {"extract", {"manifest.inspect", "archive.extract"}},
        {"build", {"build.phase"}},
        {"link", {"store.register", "generation.prepare", "generation.activate"}}};
    const auto role = vocabulary.find(grant.role);
    require(role != vocabulary.end(), "unsupported helper role");
    require(bounded_text(grant.caller, 256), "invalid authenticated caller identity");
    require(hex(grant.instance_id, 32) && hex(grant.operation_id, 32) && hex(grant.session_id, 32),
            "invalid helper instance, operation or session identity");
    require(grant.plan_digest.starts_with("sha256:") &&
                hex(std::string_view{grant.plan_digest}.substr(7), 64),
            "invalid authorized plan digest");
    require(!grant.capabilities.empty() &&
                std::includes(role->second.begin(), role->second.end(), grant.capabilities.begin(),
                              grant.capabilities.end()),
            "capability outside helper role vocabulary");
    return {{"caller", grant.caller},
            {"role", grant.role},
            {"instance_id", grant.instance_id},
            {"operation_id", grant.operation_id},
            {"session_id", grant.session_id},
            {"plan_digest", grant.plan_digest},
            {"capabilities", grant.capabilities}};
}
void version_and_binding(const core::Json& message, const core::Json& expected) {
    require(message.at("format").is_number_integer() && message.at("format") == 2,
            "unsupported helper protocol version");
    require(message.at("binding") == expected, "helper authority binding mismatch");
}
std::uint64_t sequence(const core::Json& message) {
    const auto& value = message.at("sequence");
    require(value.is_number_integer() && value > 0 && value <= maximum_sequence,
            "invalid helper request sequence");
    return value.get<std::uint64_t>();
}
void outcome_shape(const core::Json& observations, const core::Json& effects,
                   const core::Json& receipt) {
    require(observations.is_array() && effects.is_array() &&
                (receipt.is_null() || receipt.is_object()),
            "invalid helper outcome shape");
    for (const auto* list : {&observations, &effects}) {
        require(std::all_of(list->begin(), list->end(),
                            [](const core::Json& value) {
                                return value.is_object();
                            }),
                "helper observations and effects must contain objects");
    }
}
void failure_shape(const core::Failure& failure) {
    require(bounded_text(failure.code, 80) && bounded_text(failure.message, 4096),
            "invalid helper failure");
}
} // namespace
core::Result<std::optional<core::Json>> read_frame(std::istream& input) {
    return core::capture([&]() -> std::optional<core::Json> {
        std::array<unsigned char, 4> header{};
        input.read(reinterpret_cast<char*>(header.data()),
                   static_cast<std::streamsize>(header.size()));
        if (input.gcount() == 0 && input.eof() && !input.bad()) {
            return std::nullopt;
        }
        require(input.gcount() == 4 && !input.bad(), "truncated helper frame header");
        std::uint32_t length = 0;
        for (const auto byte : header) {
            length = (length << 8) | byte;
        }
        require(length > 0 && length <= maximum_frame, "helper frame exceeds bounds");
        std::string bytes(length, '\0');
        input.read(bytes.data(), static_cast<std::streamsize>(length));
        require(input.gcount() == static_cast<std::streamsize>(length) && !input.bad(),
                "truncated helper frame body");
        auto message = core::take(core::parse_json(bytes));
        require(message.is_object(), "helper frame must contain an object");
        return message;
    });
}
core::Result<std::string> encode_frame(const core::Json& message) {
    return core::capture([&] {
        require(message.is_object(), "helper frame must contain an object");
        // Validate programmatic JSON too: nlohmann serializes nonfinite numbers
        // as null, so reject them explicitly instead of silently changing a receipt.
        std::vector<std::pair<const core::Json*, unsigned>> pending{{&message, 0}};
        std::size_t minimum_bytes = 1;
        const auto charge = [&](std::size_t size) {
            require(size <= maximum_frame - minimum_bytes, "helper frame exceeds bounds");
            minimum_bytes += size;
        };
        while (!pending.empty()) {
            const auto [value, depth] = pending.back();
            pending.pop_back();
            require(depth <= 64 && !value->is_binary() && !value->is_discarded(),
                    "invalid helper JSON value");
            if (value->is_string()) {
                charge(value->get_ref<const std::string&>().size());
            }
            if (value->is_number_float()) {
                require(std::isfinite(value->get<double>()), "nonfinite helper number");
            }
            if (value->is_structured()) {
                charge(value->size());
                if (value->is_object()) {
                    for (const auto& item : value->items()) {
                        charge(item.key().size());
                    }
                }
                for (const auto& child : *value) {
                    pending.emplace_back(&child, depth + 1);
                }
            }
        }
        const auto payload = message.dump();
        require(!payload.empty() && payload.size() <= maximum_frame, "helper frame exceeds bounds");
        core::take(core::parse_json(payload)); // Same nesting and string policy as received frames.
        const auto length = static_cast<std::uint32_t>(payload.size());
        std::string framed;
        for (unsigned shift : {24U, 16U, 8U, 0U}) {
            framed.push_back(static_cast<char>((length >> shift) & 255U));
        }
        return framed + payload;
    });
}
Session::Session(const Grant& grant)
    : binding_(helper::binding(grant)), capabilities_(grant.capabilities) {}
core::Result<core::Json> Session::execute(const core::Json& message, const Handler& handler) {
    bool admitted = false;
    auto result = core::capture([&] {
        std::lock_guard lock{mutex_};
        core::take(encode_frame(message));
        fields(message, {"format", "binding", "sequence", "command", "arguments"});
        version_and_binding(message, binding_);
        const auto number = sequence(message);
        if (number <= sequence_) {
            throw core::Error("helper sequence already admitted; look up the durable outcome",
                              "helper_replay");
        }
        require(number == sequence_ + 1, "helper request is out of sequence");
        require(message.at("command").is_string() && message.at("arguments").is_object(),
                "invalid helper command or arguments");
        const auto command = message.at("command").get<std::string>();
        require(capabilities_.contains(command), "helper command lacks granted capability");
        require(static_cast<bool>(handler), "missing helper operation implementation");
        sequence_ = number;
        admitted = true;
        const Request request{number, command, message.at("arguments")};
        Outcome outcome;
        try {
            handler(request, outcome);
        } catch (const core::Error& error) {
            outcome.failure = core::Failure{error.code, error.what()};
        } catch (const std::exception& error) {
            outcome.failure = core::Failure{"helper_execution", error.what()};
        }
        // A failure may follow effects. Preserve accumulated observations,
        // effects and receipts; never manufacture an unchanged-state outcome.
        outcome_shape(outcome.observations, outcome.effects, outcome.receipt);
        core::Json failure = nullptr;
        if (outcome.failure) {
            failure_shape(*outcome.failure);
            failure = {{"code", outcome.failure->code}, {"message", outcome.failure->message}};
        }
        core::Json response{{"format", 2},
                            {"binding", binding_},
                            {"sequence", number},
                            {"observations", outcome.observations},
                            {"effects", outcome.effects},
                            {"receipt", outcome.receipt},
                            {"failure", failure}};
        core::take(encode_frame(response));
        return response;
    });
    if (!result && admitted) {
        result.error().code = "helper_outcome_unknown";
    }
    return result;
}
core::Result<Outcome> Session::verify_response(const core::Json& message,
                                               std::uint64_t expected_sequence) const {
    return core::capture([&] {
        core::take(encode_frame(message));
        fields(message,
               {"format", "binding", "sequence", "observations", "effects", "receipt", "failure"});
        version_and_binding(message, binding_);
        require(sequence(message) == expected_sequence, "helper response sequence mismatch");
        outcome_shape(message.at("observations"), message.at("effects"), message.at("receipt"));
        Outcome outcome{message.at("observations"), message.at("effects"), message.at("receipt"),
                        std::nullopt};
        const auto& failure = message.at("failure");
        if (!failure.is_null()) {
            fields(failure, {"code", "message"});
            outcome.failure = core::Failure{failure.at("code").get<std::string>(),
                                            failure.at("message").get<std::string>()};
            failure_shape(*outcome.failure);
        }
        return outcome;
    });
}
} // namespace aslice::helper
