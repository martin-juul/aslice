#include "core/lock_wait.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/simulator.hpp"
#include "platform/target_filesystem.hpp"
#include "platform/target_filesystem_simulator.hpp"
#include "platform/wait_clock_simulator.hpp"
#include <exception>
#include <iostream>
#include <memory>
#include <stop_token>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    using aslice::core::Json;
    try {
        aslice::core::require(argc == 5 && std::string(argv[1]) == "--session" &&
                                  std::string(argv[3]) == "--script",
                              "expected session and script");
        aslice::platform::Simulator simulator{aslice::platform::HostPath{argv[2]}};
        aslice::platform::SimulatorFileSystem filesystem{simulator};
        aslice::platform::SimulatorWaitClock clock{simulator};
        const auto script = aslice::core::take(aslice::core::read_json(argv[4]));
        const auto timeout = aslice::core::take(
            aslice::core::parse_lock_timeout(script.at("timeout").get<std::string>()));
        std::stop_source cancellation;
        aslice::core::LockWait waiting{clock, script.at("authorized").get<bool>(), timeout,
                                       cancellation.get_token()};
        std::vector<std::unique_ptr<aslice::platform::FileLock>> locks;
        for (const auto& action : script.at("actions")) {
            const auto operation = action.at("operation").get<std::string>();
            auto result = aslice::core::capture([&] {
                if (operation == "lock") {
                    locks.push_back(filesystem.wait_lock(
                        aslice::platform::TargetPath{action.at("root").get<std::string>()}, waiting,
                        {"client-state", "test", "unknown"}));
                } else if (operation == "cancel") {
                    cancellation.request_stop();
                } else if (operation == "recover") {
                    waiting.begin_recovery();
                } else {
                    throw aslice::core::Error("unsupported driver action");
                }
            });
            std::cout << Json{{"outcome", result ? "ok" : result.error().code},
                              {"elapsed_ms", waiting.elapsed().count()},
                              {"remaining_ms", waiting.remaining().count()}}
                             .dump()
                      << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
