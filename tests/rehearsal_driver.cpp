#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/rehearsal.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        aslice::core::require(argc == 5 && std::string(argv[1]) == "--session" &&
                                  std::string(argv[3]) == "--script",
                              "expected --session FILE --script FILE");
        aslice::platform::Rehearsal platform{aslice::platform::HostPath{argv[2]}};
        const auto script = aslice::core::take(aslice::core::read_json(argv[4]));
        for (const auto& action : script) {
            const auto capability = action.at("capability").get<std::string>();
            const auto operation = action.at("operation").get<std::string>();
            const auto arguments = action.value("arguments", aslice::core::Json::object());
            if (capability == "filesystem") {
                const aslice::platform::TargetPath checked{arguments.at("path").get<std::string>()};
                (void)checked;
            }
            const auto response = platform.request(capability, operation, arguments);
            if (response) {
                auto output = *response;
                if (!output.at("failure").is_null()) {
                    output["error"] = output.at("failure").at("code");
                    output["message"] = output.at("failure").at("message");
                }
                std::cout << output.dump() << '\n';
            } else {
                std::cout << aslice::core::Json{{"error", response.error().code},
                                                {"message", response.error().message}}
                                 .dump()
                          << '\n';
                if (response.error().code == "transport") {
                    return 3;
                }
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
