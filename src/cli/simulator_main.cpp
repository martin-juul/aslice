#include "cli/registry.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/simulator.hpp"
#include "platform/target_filesystem_simulator.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        aslice::core::require(argc >= 4 && std::string(argv[1]) == "--session",
                              "usage: aslice-simulator --session FILE COMMAND...");
        aslice::platform::Simulator platform{aslice::platform::HostPath{argv[2]}};
        const auto observation = aslice::core::take(platform.request("machine", "observe"));
        aslice::core::require(observation.at("failure").is_null(), "machine observation refused");
        aslice::platform::SimulatorFileSystem filesystem{platform};
        return aslice::cli::dispatch(argc - 2, argv + 2, filesystem);
    } catch (const std::exception& error) {
        std::cerr << "aslice-simulator: " << error.what() << '\n';
        return 2;
    }
}
