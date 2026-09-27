#include "core/result.hpp"
#include "core/support.hpp"
#include "helper/protocol.hpp"
#include "package/manifest.hpp"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

namespace {
using aslice::core::Json;
using aslice::core::require;
using aslice::core::take;
using aslice::helper::Grant;
using aslice::helper::Outcome;
using aslice::helper::Request;
using aslice::helper::Session;
Grant grant() {
    return {"uid:501",
            "extract",
            std::string(32, 'a'),
            std::string(32, 'b'),
            std::string(32, 'c'),
            "sha256:" + std::string(64, 'd'),
            {"manifest.inspect"}};
}
Json request(const Session& session, std::uint64_t sequence = 1) {
    return {{"format", 2},
            {"binding", session.binding()},
            {"sequence", sequence},
            {"command", "manifest.inspect"},
            {"arguments", Json::object()}};
}
std::string raw_frame(const std::string& bytes) {
    const auto length = static_cast<std::uint32_t>(bytes.size());
    std::string result;
    for (unsigned shift : {24U, 16U, 8U, 0U}) {
        result.push_back(static_cast<char>((length >> shift) & 255U));
    }
    return result + bytes;
}
void framing() {
    using aslice::helper::encode_frame;
    using aslice::helper::read_frame;
    const auto frame = take(encode_frame({{"format", 2}, {"text", "bound bytes"}}));
    std::istringstream stream{frame + frame};
    const auto first = take(read_frame(stream));
    require(first.has_value() && first == take(read_frame(stream)), "frame boundaries lost");
    require(!take(read_frame(stream)).has_value(), "clean EOF rejected");
    for (std::size_t length = 1; length < frame.size(); ++length) {
        std::istringstream truncated{frame.substr(0, length)};
        require(!read_frame(truncated), "truncated frame accepted");
    }
    for (const auto& bytes : {std::string(4, '\0'), std::string("\x00\x10\x00\x01", 4),
                              raw_frame("[]"), raw_frame("{\"a\":1,\"a\":2}"),
                              raw_frame("{\"a\":NaN}"), raw_frame("{\"a\":Infinity}")}) {
        std::istringstream malformed{bytes};
        require(!read_frame(malformed), "invalid framed JSON accepted");
    }
    require(!encode_frame({{"x", std::string(aslice::helper::maximum_frame, 'x')}}),
            "oversized output accepted");
    const auto exact =
        take(encode_frame({{"x", std::string(aslice::helper::maximum_frame - 8, 'x')}}));
    require(exact.size() == aslice::helper::maximum_frame + 4, "exact frame boundary rejected");
    std::istringstream boundary{exact};
    require(take(read_frame(boundary)).has_value(), "maximum permitted frame refused");
    require(!encode_frame({{"x", std::string(aslice::helper::maximum_frame - 7, 'x')}}),
            "frame one byte beyond limit accepted");
    require(!encode_frame({{"x", std::numeric_limits<double>::infinity()}}),
            "nonfinite output changed to null");
    Json nested = Json::object();
    for (unsigned level = 0; level != 66; ++level) {
        nested = Json{{"child", nested}};
    }
    require(!encode_frame(nested), "excessive output nesting accepted");
    std::istringstream deep{raw_frame(nested.dump())};
    require(!read_frame(deep), "excessive input nesting accepted");
}
void admission() {
    Session session{grant()};
    unsigned calls = 0;
    const auto handler = [&](const Request&, Outcome&) {
        ++calls;
    };
    const auto valid = request(session);
    for (const auto& field :
         {"caller", "role", "instance_id", "operation_id", "session_id", "plan_digest"}) {
        auto altered = valid;
        altered["binding"][field] = "substituted";
        require(!session.execute(altered, handler), "substituted grant binding accepted");
    }
    auto changed = valid;
    changed["binding"]["capabilities"] = {"manifest.inspect", "archive.extract"};
    require(!session.execute(changed, handler), "capability escalation accepted");
    for (const Json& version : {Json(1), Json(3), Json(2.0), Json(true), Json("2")}) {
        changed = valid;
        changed["format"] = version;
        require(!session.execute(changed, handler), "unsupported version accepted");
    }
    for (const Json& number :
         {Json(0), Json(-1), Json(1.0), Json(true), Json(9007199254740992ULL)}) {
        changed = valid;
        changed["sequence"] = number;
        require(!session.execute(changed, handler), "unsafe request sequence accepted");
    }
    changed = valid;
    changed["command"] = "archive.extract";
    require(!session.execute(changed, handler), "ungranted operation admitted");
    changed = valid;
    changed["unknown"] = true;
    require(!session.execute(changed, handler), "unknown field accepted");
    changed = valid;
    changed.erase("arguments");
    require(!session.execute(changed, handler), "missing field accepted");
    require(!session.execute(request(session, 2), handler), "sequence gap accepted");
    require(calls == 0, "refused request executed effects");
    const auto response = take(session.execute(valid, handler));
    require(calls == 1 && session.verify_response(response, 1).has_value(), "valid request failed");
    const auto duplicate = session.execute(valid, handler);
    require(!duplicate && duplicate.error().code == "helper_replay" && calls == 1,
            "duplicate request reexecuted");
    auto restarted_grant = grant();
    restarted_grant.session_id = std::string(32, 'e');
    Session restarted{restarted_grant};
    require(!restarted.execute(valid, handler), "old process session accepted after restart");
    require(!restarted.verify_response(response, 1), "old outcome accepted under a new session");
    require(!session.verify_response(response, 2), "unrelated sequence response accepted");
}
void roles() {
    for (const auto& role : {"system", "publisher", "release-signer", "unknown"}) {
        auto value = grant();
        value.role = role;
        require(!aslice::core::capture([&] {
            Session invalid{value};
        }),
                "unsupported helper authority admitted");
    }
    auto value = grant();
    value.capabilities.insert("generation.activate");
    require(!aslice::core::capture([&] {
        Session invalid{value};
    }),
            "cross-role capability admitted");
    value = grant();
    value.caller = "";
    require(!aslice::core::capture([&] {
        Session invalid{value};
    }),
            "missing authenticated identity accepted");
}
void effects_and_lost_outcomes() {
    Session session{grant()};
    unsigned mutations = 0;
    const auto handler = [&](const Request&, Outcome& outcome) {
        ++mutations;
        outcome.observations.push_back({{"before", "a"}});
        outcome.effects.push_back({{"write", "b"}});
        outcome.receipt = {{"journal_record", "receipt-reference"}};
        throw aslice::core::Error("injected failure after effect", "io");
    };
    const auto message = request(session);
    const auto reply = take(session.execute(message, handler));
    const auto outcome = take(session.verify_response(reply, 1));
    require(outcome.failure.has_value() && outcome.failure->code == "io" &&
                outcome.effects.size() == 1 && outcome.observations.size() == 1 &&
                !outcome.receipt.is_null(),
            "failure erased effects or receipt");
    require(!session.execute(message, handler) && mutations == 1,
            "lost acknowledgement repeated effect");
    auto forged = reply;
    forged["effects"] = "none";
    require(!session.verify_response(forged, 1), "malformed effect report accepted");
    forged = reply;
    forged["failure"]["retry_safe"] = true;
    require(!session.verify_response(forged, 1), "unapproved failure fields accepted");
    // Response encoding can fail after an effect. The sequence remains consumed.
    const auto oversized = request(session, 2);
    const auto unknown = session.execute(oversized, [&](const Request&, Outcome& result) {
        ++mutations;
        result.effects.push_back({{"bytes", std::string(aslice::helper::maximum_frame, 'x')}});
    });
    require(!unknown && unknown.error().code == "helper_outcome_unknown",
            "post-effect output failure was not reported as uncertain");
    require(!session.execute(oversized, handler) && mutations == 2,
            "output failure allowed replay");
}
void concurrency() {
    Session session{grant()};
    std::atomic<unsigned> effects{0};
    std::atomic<unsigned> admitted{0};
    std::vector<std::jthread> clients;
    const auto message = request(session);
    for (unsigned index = 0; index != 8; ++index) {
        clients.emplace_back([&] {
            if (session.execute(message, [&](const Request&, Outcome&) {
                    ++effects;
                })) {
                ++admitted;
            }
        });
    }
    clients.clear();
    require(admitted == 1 && effects == 1, "concurrent duplicate executed more than once");
}
void real_manifest(const std::string& path) {
    Session session{grant()};
    auto message = request(session);
    message["arguments"]["manifest"] = take(aslice::core::read_json(path));
    std::istringstream channel{take(aslice::helper::encode_frame(message))};
    const auto received = take(aslice::helper::read_frame(channel));
    require(received.has_value(), "missing request");
    const auto result =
        take(session.execute(*received, [](const Request& request, Outcome& outcome) {
            auto manifest =
                take(aslice::package::Manifest::parse(request.arguments.at("manifest")));
            outcome.observations.push_back(manifest.inspect());
        }));
    const auto verified = take(session.verify_response(result, 1));
    require(!verified.failure.has_value() && verified.effects.empty() &&
                verified.observations.size() == 1,
            "manifest inspection through admitted request failed");
}
} // namespace
int main(int argc, char** argv) {
    static_assert(!std::is_copy_constructible_v<Session>);
    try {
        require(argc == 2, "expected manifest fixture path");
        framing();
        admission();
        roles();
        effects_and_lost_outcomes();
        concurrency();
        real_manifest(argv[1]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
