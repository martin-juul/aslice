#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>

// Windows leaf headers require the WinSock umbrella definitions first.
#include <inaddr.h>
#include <minwindef.h>
#else
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
// glibc exports timeval through this public header, not a private bits header.
// NOLINTNEXTLINE(misc-include-cleaner)
#include <sys/time.h>
#include <unistd.h>
#endif
#include "core/result.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/simulator.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>

namespace aslice::platform {
namespace {
constexpr std::size_t maximum_frame = 1024 * 1024;
#ifdef _WIN32
// MinGW defines these WinSock public types in private psdk_inc headers.
// NOLINTNEXTLINE(misc-include-cleaner)
using Socket = SOCKET;
// NOLINTNEXTLINE(misc-include-cleaner)
constexpr Socket invalid_socket = INVALID_SOCKET;
struct Network {
    Network() {
        // NOLINTNEXTLINE(misc-include-cleaner)
        WSADATA data{};
        core::require(WSAStartup(MAKEWORD(2, 2), &data) == 0, "socket initialization failed");
    }
    ~Network() {
        WSACleanup();
    }
};
void close_socket(Socket socket) {
    closesocket(socket);
}
#else
using Socket = int;
constexpr Socket invalid_socket = -1;
struct Network {};
void close_socket(Socket socket) {
    close(socket);
}
#endif
struct Connection {
    Socket value = invalid_socket;
    ~Connection() {
        if (value != invalid_socket) {
            close_socket(value);
        }
    }
    Connection() = default;
    Connection(const Connection&) = delete;
    Connection& operator=(const Connection&) = delete;
};
void transfer(Socket socket, char* data, std::size_t size, bool writing) {
    while (size != 0) {
#ifdef _WIN32
        const auto count = static_cast<int>(size);
        const int flags = 0;
#else
        const auto count = size;
        const int flags = writing ? MSG_NOSIGNAL : 0;
#endif
        const auto done = writing ? send(socket, data, count, flags) : recv(socket, data, count, 0);
        if (done <= 0) {
            throw core::Error("simulator transport closed or timed out; outcome may be unknown",
                              "transport");
        }
        data += done;
        size -= static_cast<std::size_t>(done);
    }
}
core::Json exchange(Socket socket, const core::Json& value) {
    auto payload = value.dump();
    core::require(payload.size() <= maximum_frame, "simulator frame exceeds limit");
    const auto size = static_cast<std::uint32_t>(payload.size());
    std::array<char, 4> header{static_cast<char>(size >> 24), static_cast<char>(size >> 16),
                               static_cast<char>(size >> 8), static_cast<char>(size)};
    transfer(socket, header.data(), header.size(), true);
    transfer(socket, payload.data(), payload.size(), true);
    transfer(socket, header.data(), header.size(), false);
    std::uint32_t length = 0;
    for (const auto byte : header) {
        length = (length << 8) | static_cast<unsigned char>(byte);
    }
    core::require(length != 0 && length <= maximum_frame, "invalid simulator response length");
    payload.resize(length);
    transfer(socket, payload.data(), payload.size(), false);
    return core::take(core::parse_json(payload));
}
} // namespace

struct Simulator::Impl {
    [[maybe_unused]] Network network;
    Connection connection;
    std::uint64_t sequence = 0;
    explicit Impl(const HostPath& session) {
        const auto descriptor = core::take(core::read_json(session.path()));
        sequence = descriptor.value("sequence", std::uint64_t{0});
        core::require(descriptor.at("version") == 1 && descriptor.at("host") == "127.0.0.1",
                      "unsupported simulator endporeloadint");
        const auto port = descriptor.at("port").get<unsigned>();
        core::require(port > 0 && port <= 65535, "invalid simulator port");
        connection.value = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (connection.value == invalid_socket) {
            throw core::Error("cannot create simulator socket", "transport");
        }
        const int no_delay = 1;
        core::require(setsockopt(connection.value, IPPROTO_TCP, TCP_NODELAY,
                                 reinterpret_cast<const char*>(&no_delay), sizeof(no_delay)) == 0,
                      "cannot configure simulator framing latency");
#ifdef _WIN32
        const DWORD timeout = 10000;
        const auto* timeout_data = reinterpret_cast<const char*>(&timeout);
#else
        // NOLINTNEXTLINE(misc-include-cleaner)
        const timeval timeout{10, 0};
        const auto* timeout_data = &timeout;
#endif
        // Socket constants come from the public socket headers on each host.
        // NOLINTBEGIN(misc-include-cleaner)
        core::require(setsockopt(connection.value, SOL_SOCKET, SO_RCVTIMEO, timeout_data,
                                 sizeof(timeout)) == 0 &&
                          setsockopt(connection.value, SOL_SOCKET, SO_SNDTIMEO, timeout_data,
                                     sizeof(timeout)) == 0,
                      "cannot configure simulator timeout");
        // NOLINTEND(misc-include-cleaner)
        // NOLINTNEXTLINE(misc-include-cleaner)
        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_port = htons(static_cast<std::uint16_t>(port));
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        // NOLINTNEXTLINE(misc-include-cleaner)
        core::require(connect(connection.value, reinterpret_cast<const sockaddr*>(&address),
                              sizeof(address)) == 0,
                      "cannot connect to simulator server");
        const auto response = exchange(connection.value, {{"version", 1},
                                                          {"operation", "hello"},
                                                          {"identity", descriptor.at("identity")},
                                                          {"token", descriptor.at("token")}});
        core::require(response == core::Json{{"version", 1}, {"authenticated", true}},
                      "simulator authentication refused");
    }
};
Simulator::Simulator(const HostPath& session) : implementation_(std::make_unique<Impl>(session)) {}
Simulator::~Simulator() = default;
core::Result<core::Json> Simulator::request(const std::string& capability,
                                            const std::string& operation,
                                            const core::Json& arguments,
                                            const core::Json& preconditions) {
    return core::capture([&] {
        const auto id = ++implementation_->sequence;
        const auto response =
            exchange(implementation_->connection.value, {{"version", 1},
                                                         {"id", id},
                                                         {"capability", capability},
                                                         {"operation", operation},
                                                         {"arguments", arguments},
                                                         {"preconditions", preconditions}});
        core::require(response.at("version") == 1 && response.at("id") == id,
                      "mismatched simulator response");
        // An OS failure can accompany effects. Preserve the whole envelope so
        // recovery callers can inspect receipts rather than infer no mutation.
        core::require(response.contains("failure") && response.contains("effects") &&
                          response.contains("receipt") && response.contains("result"),
                      "incomplete simulator response");
        return response;
    });
}
core::Result<core::Json> Simulator::filesystem(const std::string& operation, const TargetPath& path,
                                               core::Json arguments) {
    arguments["path"] = path.string();
    return request("filesystem", operation, arguments);
}
} // namespace aslice::platform
