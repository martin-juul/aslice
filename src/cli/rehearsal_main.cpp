#include "cli/registry.hpp"
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/rehearsal.hpp"
#include "platform/target_filesystem_rehearsal.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        aslice::core::require(argc >= 4 && std::string(argv[1]) == "--session",
                              "usage: aslice-rehearsal --session FILE COMMAND...");
        aslice::platform::Rehearsal platform{aslice::platform::HostPath{argv[2]}};
        const auto observation = aslice::core::take(platform.request("machine", "observe"));
        aslice::core::require(observation.at("failure").is_null(), "machine observation refused");
        aslice::platform::RehearsalFileSystem filesystem{platform};
        return aslice::cli::dispatch(argc - 2, argv + 2, filesystem);
    } catch (const std::exception& error) {
        std::cerr << "aslice-rehearsal: " << error.what() << '\n';
        return 2;
    }
}
