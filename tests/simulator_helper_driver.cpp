#include "core/result.hpp"
#include "core/support.hpp"
#include "helper/inspection.hpp"
#include "helper/protocol.hpp"
#include "platform/paths.hpp"
#include "platform/simulator.hpp"
#include <algorithm>
#include <cstddef>
#include <exception>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <string_view>
#include <utility>

namespace {
using aslice::core::Json;
using aslice::core::require;
using aslice::core::take;
std::string hex(std::string_view bytes) {
    constexpr std::string_view digits = "0123456789abcdef";
    std::string result;
    for (unsigned char byte : bytes) {
        result += digits[byte >> 4];
        result += digits[byte & 15];
    }
    return result;
}
std::string unhex(const std::string& text) {
    require(text.size() % 2 == 0, "invalid channel bytes");
    std::string result;
    for (std::size_t index = 0; index < text.size(); index += 2) {
        constexpr std::string_view digits = "0123456789abcdef";
        const auto high = digits.find(text[index]);
        const auto low = digits.find(text[index + 1]);
        require(high != std::string_view::npos && low != std::string_view::npos, "invalid hex");
        result += static_cast<char>((high << 4) | low);
    }
    return result;
}
Json message(const std::string& bytes) {
    std::istringstream input{bytes};
    auto value = take(aslice::helper::read_frame(input));
    require(value.has_value() && input.peek() == std::char_traits<char>::eof(),
            "expected exactly one complete helper frame");
    return std::move(*value);
}
} // namespace
int main(int argc, char** argv) {
    try {
        require(argc == 3, "expected session and inherited endpoint");
        auto platform =
            std::make_unique<aslice::platform::Simulator>(aslice::platform::HostPath{argv[1]});
        const std::string endpoint{argv[2]};
        const auto identity =
            take(platform->request("channel", "observe", {{"endpoint", endpoint}}));
        require(identity.at("failure").is_null(), "inherited endpoint unavailable");
        std::cout << identity.dump() << '\n';
        std::cout.flush();
        std::string outgoing;
        std::string incoming;
        std::unique_ptr<aslice::helper::Session> session;
        bool inspected = false;
        bool poisoned = false;
        for (std::string line; std::getline(std::cin, line);) {
            const auto action = take(aslice::core::parse_json(line));
            const auto command = action.at("command").get<std::string>();
            if (command == "exit") {
                break;
            }
            const auto result = aslice::core::capture([&]() -> Json {
                if (command == "disconnect") {
                    platform.reset();
                    return {{"disconnected", true}};
                }
                if (command == "request") {
                    require(!session && !poisoned, "request already issued or channel uncertain");
                    const auto& manifest = action.at("manifest");
                    // Deterministic test identities; production launchers mint fresh identities.
                    aslice::helper::Grant grant{
                        "simulated-process:" + identity.at("result").at("owner").get<std::string>(),
                        "extract",
                        std::string(32, 'a'),
                        std::string(32, 'b'),
                        std::string(32, 'c'),
                        "sha256:" + take(aslice::core::digest(manifest.dump())),
                        {"manifest.inspect"}};
                    session = std::make_unique<aslice::helper::Session>(grant);
                    outgoing = take(aslice::helper::encode_frame({{"format", 2},
                                                                  {"binding", session->binding()},
                                                                  {"sequence", 1},
                                                                  {"command", "manifest.inspect"},
                                                                  {"arguments", manifest}}));
                    return {{"remaining", outgoing.size()}};
                }
                if (command == "inspect") {
                    require(!inspected && !poisoned,
                            "inspection already admitted or channel uncertain");
                    inspected = true;
                    const auto caller =
                        "simulated-process:" + identity.at("result").at("peer").get<std::string>();
                    outgoing = take(aslice::helper::encode_frame(
                        take(aslice::helper::inspect_message(message(incoming), caller))));
                    return {{"remaining", outgoing.size()}};
                }
                if (command == "verify") {
                    require(session != nullptr && !poisoned, "no request or channel uncertain");
                    const auto outcome = take(session->verify_response(message(incoming), 1));
                    require(!outcome.failure, "inspection failed");
                    return {{"observations", outcome.observations}, {"effects", outcome.effects}};
                }
                require(platform != nullptr && !poisoned,
                        "channel unavailable or outcome uncertain");
                require(command == "send" || command == "receive", "unsupported test action");
                const auto limit = action.value("limit", std::size_t{16384});
                require(limit > 0 && limit <= 16384, "invalid channel transfer size");
                Json arguments{{"endpoint", endpoint}};
                if (command == "send") {
                    arguments["hex"] = hex(std::string_view{outgoing}.substr(0, limit));
                } else {
                    arguments["length"] = limit;
                }
                const auto response = platform->request("channel", command, arguments);
                if (!response) {
                    poisoned = true;
                    throw aslice::core::Error(response.error().message, response.error().code);
                }
                if (!response->at("failure").is_null()) {
                    poisoned = response->at("failure").at("code") != "would-block";
                    return *response;
                }
                if (command == "send") {
                    const auto count = response->at("result").at("written").get<std::size_t>();
                    require(count <= std::min(limit, outgoing.size()), "invalid short-write count");
                    outgoing.erase(0, count);
                } else {
                    incoming += unhex(response->at("result").at("hex").get<std::string>());
                    require(incoming.size() <= aslice::helper::maximum_frame + 4,
                            "incoming frame oversized");
                }
                auto output = *response;
                output["remaining"] = outgoing.size();
                output["received"] = incoming.size();
                return output;
            });
            const Json output =
                result ? *result
                       : Json{{"error", result.error().code}, {"message", result.error().message}};
            std::cout << output.dump() << '\n';
            std::cout.flush();
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
