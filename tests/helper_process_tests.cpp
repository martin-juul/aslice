#include "core/support.hpp"
#include "package/manifest.hpp"
#include "platform/helper_process.hpp"
#include "platform/paths.hpp"
#include <array>
#include <chrono>
#include <cstddef>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stop_token>
#include <string_view>
#include <thread>
#include <vector>

int main(int argc, char** argv) {
    using aslice::core::require;
    using aslice::core::take;
    // Deliberately unresponsive peer used only by this test executable.
    if (argc > 1 && std::string_view{argv[1]} == "--internal-manifest-inspection-v2") {
        std::this_thread::sleep_for(std::chrono::seconds{20});
        return 0;
    }
    try {
        require(argc == 3, "expected manager and fixture paths");
#if !defined(_WIN32) && !defined(__linux__)
        std::cout << "native helper adapter unavailable on this host\n";
        return 77;
#endif
        const aslice::platform::HostPath executable{std::filesystem::absolute(argv[1])};
        const auto manifest = take(aslice::core::read_json(argv[2]));
        const auto expected = take(aslice::package::Manifest::parse(manifest)).inspect();
        require(take(aslice::platform::inspect_in_helper(executable, manifest)) == expected,
                "native helper differs from shared application inspection");
        const auto invalid =
            aslice::platform::inspect_in_helper(executable, aslice::core::Json::object());
        const auto direct_failure = aslice::package::Manifest::parse(aslice::core::Json::object());
        require(!invalid && !direct_failure &&
                    invalid.error().code == direct_failure.error().code &&
                    invalid.error().message == direct_failure.error().message,
                invalid ? "helper accepted invalid manifest"
                        : "helper application failure lost: " + invalid.error().code + ": " +
                              invalid.error().message);
        std::stop_source cancelled;
        cancelled.request_stop();
        const auto cancelled_result = aslice::platform::inspect_in_helper(
            executable, manifest, std::chrono::seconds{30}, cancelled.get_token());
        require(!cancelled_result && cancelled_result.error().code == "cancelled",
                "cancelled launch accepted");
        require(!aslice::platform::inspect_in_helper(executable, manifest,
                                                     std::chrono::milliseconds{0}),
                "zero deadline accepted");
        require(!aslice::platform::inspect_in_helper(executable, manifest, std::chrono::minutes{6}),
                "unbounded deadline accepted");
        require(
            !aslice::platform::inspect_in_helper(aslice::platform::HostPath{"relative"}, manifest),
            "relative executable accepted");
        require(!aslice::platform::inspect_in_helper(executable,
                                                     {{"large", std::string(1024 * 1024, 'x')}}),
                "oversized input accepted");
        const aslice::platform::HostPath unresponsive{std::filesystem::absolute(argv[0])};
        const auto before = std::chrono::steady_clock::now();
        const auto timed = aslice::platform::inspect_in_helper(unresponsive, manifest,
                                                               std::chrono::milliseconds{100});
        require(!timed && timed.error().code == "timeout", "unresponsive helper did not time out");
        std::stop_source running;
        std::jthread cancel([&] {
            std::this_thread::sleep_for(std::chrono::milliseconds{50});
            running.request_stop();
        });
        const auto interrupted = aslice::platform::inspect_in_helper(
            unresponsive, manifest, std::chrono::seconds{30}, running.get_token());
        require(!interrupted && interrupted.error().code == "cancelled",
                "running helper was not cancelled");
        require(std::chrono::steady_clock::now() - before < std::chrono::seconds{5},
                "helper cleanup failed to reap promptly");
        std::vector<std::jthread> threads;
        std::array<bool, 4> passed{};
        threads.reserve(passed.size());
        for (std::size_t i = 0; i < passed.size(); ++i) {
            threads.emplace_back([&, i] {
                const auto result = aslice::platform::inspect_in_helper(executable, manifest);
                passed[i] = result && *result == expected;
            });
        }
        threads.clear();
        for (const bool result : passed) {
            require(result, "concurrent helper channel confusion");
        }
        std::cout << "native helper process checks passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
