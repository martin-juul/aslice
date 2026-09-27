#include "platform/helper_process.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include "helper/inspection.hpp"
#include "helper/protocol.hpp"
#include "platform/paths.hpp"
#include <array>
#include <charconv>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <openssl/rand.h>
#include <optional>
#include <sstream>
#include <stop_token>
#include <string>
#include <string_view>
#include <system_error>
#include <thread>
#include <utility>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
// Windows SDK leaf headers require umbrella definitions first.
// NOLINTNEXTLINE(misc-include-cleaner)
#include <windows.h>

#include <basetsd.h>
#include <errhandlingapi.h>
#include <fileapi.h>
#include <handleapi.h>
#include <minwinbase.h>
#include <minwindef.h>
#include <namedpipeapi.h>
#include <processthreadsapi.h>
#include <sddl.h>
#include <securitybaseapi.h>
#include <synchapi.h>
#include <vector>
#include <winbase.h>
#include <winerror.h>
#include <winnt.h>
#elif defined(__linux__)
#include <cerrno>
#include <fcntl.h>
#include <limits>
#include <signal.h>
#include <spawn.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
extern char** environ;
#endif

namespace aslice::platform {
namespace {
using core::Json;
using core::take;
constexpr std::string_view private_mode = "--internal-manifest-inspection-v2";
void check(bool value, const char* message) {
    if (!value) {
        throw core::Error(message, "helper_transport");
    }
}
#if defined(_WIN32) || defined(__linux__)
std::string nonce() {
    std::array<unsigned char, 16> bytes{};
    check(RAND_bytes(bytes.data(), static_cast<int>(bytes.size())) == 1,
          "cannot generate helper session identity");
    constexpr std::string_view digits = "0123456789abcdef";
    std::string value;
    for (const auto byte : bytes) {
        value += digits[byte >> 4];
        value += digits[byte & 15];
    }
    return value;
}
#endif
class Deadline {
  public:
    Deadline(std::chrono::milliseconds timeout, std::stop_token stop) : stop_(std::move(stop)) {
        check(timeout.count() > 0 && timeout <= std::chrono::minutes{5},
              "helper timeout must be in (0, 5 minutes]");
        end_ = std::chrono::steady_clock::now() + timeout;
    }
    void check_now() const {
        if (stop_.stop_requested()) {
            throw core::Error("read-only helper inspection cancelled", "cancelled");
        }
        if (std::chrono::steady_clock::now() >= end_) {
            throw core::Error("read-only helper inspection timed out", "timeout");
        }
    }
    void pause() const {
        check_now();
        std::this_thread::sleep_for(std::chrono::milliseconds{2});
    }

  private:
    std::chrono::steady_clock::time_point end_;
    std::stop_token stop_;
};

#if defined(_WIN32) || defined(__linux__)
#ifdef _WIN32
using Native = HANDLE;
const Native invalid = INVALID_HANDLE_VALUE;
void close_native(Native value) {
    CloseHandle(value);
}
#else
using Native = int;
constexpr Native invalid = -1;
void close_native(Native value) {
    close(value);
}
#endif
class Handle {
  public:
    explicit Handle(Native value = invalid) : value_(value) {}
    ~Handle() {
        reset();
    }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    Native get() const {
        return value_;
    }
    void reset() {
        if (value_ != invalid) {
            close_native(value_);
        }
        value_ = invalid;
    }

  private:
    Native value_;
};
std::uintptr_t parse_number(std::string_view text) {
    std::uintptr_t value = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
    check(!text.empty() && result.ec == std::errc{} && result.ptr == text.data() + text.size(),
          "invalid inherited helper handle");
    return value;
}
#ifdef _WIN32
Native parse_handle(std::string_view text) {
    // HANDLE values are serialized only for inherited-handle reexecution.
    // NOLINTNEXTLINE(performance-no-int-to-ptr)
    return reinterpret_cast<HANDLE>(parse_number(text));
}
std::string identity(HANDLE process) {
    HANDLE raw_token = nullptr;
    check(OpenProcessToken(process, TOKEN_QUERY, &raw_token), "cannot inspect helper caller token");
    const Handle token{raw_token};
    DWORD length = 0;
    GetTokenInformation(token.get(), TokenUser, nullptr, 0, &length);
    check(length > 0 && length <= 65536, "invalid caller token size");
    std::vector<unsigned char> bytes(length);
    check(GetTokenInformation(token.get(), TokenUser, bytes.data(), length, &length),
          "cannot read helper caller identity");
    LPSTR raw_sid = nullptr;
    check(ConvertSidToStringSidA(reinterpret_cast<TOKEN_USER*>(bytes.data())->User.Sid, &raw_sid),
          "cannot encode helper caller identity");
    const std::string sid{raw_sid};
    LocalFree(raw_sid);
    return "sid:" + sid;
}
#else
Native parse_handle(std::string_view text) {
    const auto value = parse_number(text);
    check(value <= static_cast<std::uintptr_t>(std::numeric_limits<int>::max()),
          "invalid inherited descriptor");
    return static_cast<int>(value);
}
std::string identity() {
    return "uid:" + std::to_string(geteuid());
}
#endif
class Channel {
  public:
    explicit Channel(Native handle) : handle_(handle) {}
    void transfer(char* bytes, std::size_t size, bool writing, const Deadline& deadline) const {
        std::size_t offset = 0;
        while (offset < size) {
            deadline.check_now();
#ifdef _WIN32
            DWORD count = 0;
            const auto amount = static_cast<DWORD>(size - offset);
            const BOOL success = writing
                                     ? WriteFile(handle_, bytes + offset, amount, &count, nullptr)
                                     : ReadFile(handle_, bytes + offset, amount, &count, nullptr);
            if (!success) {
                const auto error = GetLastError();
                check(error == ERROR_NO_DATA, "helper channel disconnected or failed");
            }
            if (count == 0) {
                deadline.pause();
                continue;
            }
#else
            const auto count = writing ? send(handle_, bytes + offset, size - offset, MSG_NOSIGNAL)
                                       : recv(handle_, bytes + offset, size - offset, 0);
            if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
                deadline.pause();
                continue;
            }
            check(count > 0, "helper channel disconnected or failed");
#endif
            offset += static_cast<std::size_t>(count);
        }
    }
    void write(const Json& value, const Deadline& deadline) const {
        auto frame = take(helper::encode_frame(value));
        transfer(frame.data(), frame.size(), true, deadline);
    }
    Json read(const Deadline& deadline) const {
        std::string frame(4, '\0');
        transfer(frame.data(), frame.size(), false, deadline);
        std::size_t length = 0;
        for (unsigned char byte : frame) {
            length = (length << 8) | byte;
        }
        check(length > 0 && length <= helper::maximum_frame, "invalid helper frame size");
        frame.resize(4 + length);
        transfer(frame.data() + 4, length, false, deadline);
        std::istringstream input{frame};
        auto value = take(helper::read_frame(input));
        check(value.has_value(), "missing helper response");
        return std::move(*value);
    }

  private:
    Native handle_;
};
class Child {
  public:
#ifdef _WIN32
    explicit Child(HANDLE process) : process_(process) {}
    ~Child() {
        if (!done_) {
            TerminateProcess(process_, 1);
            WaitForSingleObject(process_, INFINITE);
        }
        CloseHandle(process_);
    }
#else
    explicit Child(pid_t process) : process_(process) {}
    ~Child() {
        if (!done_) {
            kill(process_, SIGKILL);
            while (waitpid(process_, nullptr, 0) < 0 && errno == EINTR) {
            }
        }
    }
#endif
    Child(const Child&) = delete;
    Child& operator=(const Child&) = delete;
    void wait(const Deadline& deadline) {
        while (true) {
            deadline.check_now();
#ifdef _WIN32
            const auto result = WaitForSingleObject(process_, 0);
            check(result != WAIT_FAILED, "cannot wait for helper");
            if (result == WAIT_OBJECT_0) {
                done_ = true;
                DWORD status = 0;
                check(GetExitCodeProcess(process_, &status) && status == 0,
                      "helper exited unsuccessfully");
                return;
            }
#else
            int status = 0;
            // Public POSIX wait macros are defined in glibc's private bits headers.
            // NOLINTNEXTLINE(misc-include-cleaner)
            const auto result = waitpid(process_, &status, WNOHANG);
            if (result < 0 && errno == EINTR) {
                continue;
            }
            if (result < 0 && errno == ECHILD) {
                done_ = true; // Never signal a PID after another reaper collected it.
            }
            check(result >= 0, "cannot wait for helper");
            if (result == process_) {
                done_ = true;
                // NOLINTNEXTLINE(misc-include-cleaner)
                check(WIFEXITED(status) && WEXITSTATUS(status) == 0,
                      "helper exited unsuccessfully");
                return;
            }
#endif
            deadline.pause();
        }
    }

  private:
#ifdef _WIN32
    HANDLE process_;
#else
    pid_t process_;
#endif
    bool done_ = false;
};
Json exchange(const Channel& channel, Child& child, const Json& manifest, const std::string& caller,
              const Deadline& deadline) {
    helper::Grant grant{caller,
                        "extract",
                        nonce(),
                        nonce(),
                        nonce(),
                        "sha256:" + take(core::digest(manifest.dump())),
                        {"manifest.inspect"}};
    helper::Session session{grant};
    channel.write({{"format", 2},
                   {"binding", session.binding()},
                   {"sequence", 1},
                   {"command", "manifest.inspect"},
                   {"arguments", manifest}},
                  deadline);
    const auto outcome = take(session.verify_response(channel.read(deadline), 1));
    child.wait(deadline);
    if (outcome.failure) {
        throw core::Error(outcome.failure->message, outcome.failure->code);
    }
    check(outcome.effects.empty() && outcome.receipt.is_null() && outcome.observations.size() == 1,
          "unexpected inspection helper outcome");
    return outcome.observations.at(0);
}
void serve(const Channel& channel, const std::string& caller) {
    const Deadline deadline{std::chrono::seconds{30}, {}};
    const auto request = channel.read(deadline);
    const auto response = take(helper::inspect_message(request, caller));
    channel.write(response, deadline);
}
#endif
} // namespace

core::Result<Json> inspect_in_helper(const HostPath& executable, const Json& manifest,
                                     std::chrono::milliseconds timeout, std::stop_token stop) {
    return core::capture([&]() -> Json {
        const Deadline deadline{timeout, std::move(stop)};
        deadline.check_now();
        check(executable.path().is_absolute(), "helper executable must be an absolute host path");
        // Bound input before launching any process.
        take(helper::encode_frame({{"manifest", manifest}}));
#ifdef _WIN32
        const auto name =
            L"\\\\.\\pipe\\aslice-inspection-" + std::filesystem::path{nonce()}.wstring();
        const Handle server{CreateNamedPipeW(
            name.c_str(), PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
            PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_NOWAIT | PIPE_REJECT_REMOTE_CLIENTS, 1,
            65536, 65536, 0, nullptr)};
        check(server.get() != invalid, "cannot create helper pipe");
        SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, TRUE};
        Handle client{CreateFileW(name.c_str(), GENERIC_READ | GENERIC_WRITE, 0, &security,
                                  OPEN_EXISTING, 0, nullptr)};
        check(client.get() != invalid, "cannot connect helper pipe");
        DWORD mode = PIPE_READMODE_BYTE | PIPE_NOWAIT;
        check(SetNamedPipeHandleState(client.get(), &mode, nullptr, nullptr),
              "cannot configure helper pipe");
        const auto connected = ConnectNamedPipe(server.get(), nullptr);
        check(connected || GetLastError() == ERROR_PIPE_CONNECTED, "cannot accept helper pipe");
        const Handle parent{
            OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, TRUE, GetCurrentProcessId())};
        check(parent.get() != nullptr, "cannot retain caller process identity");
        SIZE_T size = 0;
        InitializeProcThreadAttributeList(nullptr, 1, 0, &size);
        std::vector<unsigned char> storage(size);
        auto* attributes = reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(storage.data());
        check(InitializeProcThreadAttributeList(attributes, 1, 0, &size),
              "cannot create inheritance list");
        struct Cleanup {
            LPPROC_THREAD_ATTRIBUTE_LIST value;
            ~Cleanup() {
                DeleteProcThreadAttributeList(value);
            }
        } cleanup{attributes};
        std::array<HANDLE, 2> inherited{client.get(), parent.get()};
        check(UpdateProcThreadAttribute(attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                        inherited.data(), sizeof(inherited), nullptr, nullptr),
              "cannot restrict helper inheritance");
        STARTUPINFOEXW startup{};
        startup.StartupInfo.cb = sizeof(startup);
        startup.lpAttributeList = attributes;
        auto command = L"\"" + executable.path().wstring() + L"\" " +
                       std::wstring{private_mode.begin(), private_mode.end()} + L" " +
                       std::to_wstring(reinterpret_cast<std::uintptr_t>(client.get())) + L" " +
                       std::to_wstring(reinterpret_cast<std::uintptr_t>(parent.get()));
        PROCESS_INFORMATION process{};
        check(CreateProcessW(executable.path().c_str(), command.data(), nullptr, nullptr, TRUE,
                             EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW, nullptr, nullptr,
                             &startup.StartupInfo, &process),
              "cannot launch inspection helper");
        const Handle thread{process.hThread};
        Child child{process.hProcess};
        client.reset();
        return exchange(Channel{server.get()}, child, manifest, identity(GetCurrentProcess()),
                        deadline);
#elif defined(__linux__)
        check(getuid() == geteuid() && getgid() == getegid(), "set-id helper launch refused");
        std::array<int, 2> sockets{};
        check(socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0, sockets.data()) ==
                  0,
              "cannot create helper socket pair");
        const Handle server{sockets[0]};
        Handle original_client{sockets[1]};
        Handle client{fcntl(original_client.get(), F_DUPFD_CLOEXEC, 4)};
        check(client.get() >= 4, "cannot retain helper socket");
        original_client.reset();
        posix_spawn_file_actions_t actions;
        check(posix_spawn_file_actions_init(&actions) == 0, "cannot prepare helper launch");
        struct Cleanup {
            posix_spawn_file_actions_t* value;
            ~Cleanup() {
                posix_spawn_file_actions_destroy(value);
            }
        } cleanup{&actions};
        check(posix_spawn_file_actions_addopen(&actions, 0, "/dev/null", O_RDONLY, 0) == 0 &&
                  posix_spawn_file_actions_addopen(&actions, 1, "/dev/null", O_WRONLY, 0) == 0 &&
                  posix_spawn_file_actions_addopen(&actions, 2, "/dev/null", O_WRONLY, 0) == 0 &&
                  posix_spawn_file_actions_adddup2(&actions, client.get(), 3) == 0 &&
                  posix_spawn_file_actions_addclosefrom_np(&actions, 4) == 0,
              "cannot restrict helper descriptors");
        auto path = executable.path().string();
        std::string mode{private_mode};
        std::string descriptor{"3"};
        std::string parent = std::to_string(getpid());
        std::array<char*, 5> arguments{path.data(), mode.data(), descriptor.data(), parent.data(),
                                       nullptr};
        pid_t process = 0;
        check(posix_spawn(&process, path.c_str(), &actions, nullptr, arguments.data(), environ) ==
                  0,
              "cannot launch inspection helper");
        Child child{process};
        client.reset();
        return exchange(Channel{server.get()}, child, manifest, identity(), deadline);
#else
        (void)manifest;
        throw core::Error("native helper adapter is not qualified on this host", "unsupported");
#endif
    });
}
std::optional<int> inspection_helper_entry(int argc, char** argv) {
    if (argc < 2 || argv[1] != private_mode) {
        return std::nullopt;
    }
    const auto result = core::capture([&] {
        check(argc == 4, "invalid private helper invocation");
#ifdef _WIN32
        const Handle channel{parse_handle(argv[2])};
        const Handle parent{parse_handle(argv[3])};
        ULONG server_pid = 0;
        check(GetNamedPipeServerProcessId(channel.get(), &server_pid) &&
                  server_pid == GetProcessId(parent.get()) && server_pid != GetCurrentProcessId(),
              "helper channel caller mismatch");
        const auto caller = identity(parent.get());
        check(caller == identity(GetCurrentProcess()), "cross-user helper caller refused");
        DWORD mode = PIPE_READMODE_BYTE | PIPE_NOWAIT;
        check(SetNamedPipeHandleState(channel.get(), &mode, nullptr, nullptr),
              "invalid helper pipe");
        check(SetHandleInformation(channel.get(), HANDLE_FLAG_INHERIT, 0) &&
                  SetHandleInformation(parent.get(), HANDLE_FLAG_INHERIT, 0),
              "cannot seal helper handles");
        serve(Channel{channel.get()}, caller);
#elif defined(__linux__)
        const Handle channel{parse_handle(argv[2])};
        ucred peer{};
        socklen_t length = sizeof(peer);
        // Linux socket constants are exported by sys/socket.h through private headers.
        // NOLINTNEXTLINE(misc-include-cleaner)
        check(getsockopt(channel.get(), SOL_SOCKET, SO_PEERCRED, &peer, &length) == 0 &&
                  length == sizeof(peer) && peer.pid == getppid() &&
                  static_cast<std::uintptr_t>(peer.pid) == parse_number(argv[3]) &&
                  peer.uid == geteuid() && getuid() == geteuid() && getgid() == getegid(),
              "helper channel caller mismatch");
        check(fcntl(channel.get(), F_SETFD, FD_CLOEXEC) == 0 &&
                  fcntl(channel.get(), F_SETFL, O_NONBLOCK) == 0,
              "cannot seal helper descriptor");
        serve(Channel{channel.get()}, "uid:" + std::to_string(peer.uid));
#else
        throw core::Error("native helper adapter is not qualified on this host", "unsupported");
#endif
    });
    return result ? 0 : 3;
}
} // namespace aslice::platform
