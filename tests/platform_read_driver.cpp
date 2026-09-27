// Test-only pause after opening a file, so Python can race its pathname.
#include "core/support.hpp"
#include "platform/target_filesystem.hpp"
#include <exception>
#include <iostream>
#include <string>
#include <string_view>

int main(int argc, char** argv) {
    if (argc != 3) {
        return 2;
    }
    try {
        aslice::platform::NativeFileSystem filesystem;
        std::string bytes;
        filesystem.stream(
            filesystem.absolute(argv[1]), std::stoull(argv[2]),
            [&](std::string_view chunk) {
                bytes.append(chunk);
            },
            [&](const aslice::platform::NodeStatus& metadata) {
                std::cout
                    << aslice::core::Json{{"mode", metadata.mode}, {"links", metadata.links}}.dump()
                    << '\n'
                    << std::flush;
                std::string resume;
                aslice::core::require(static_cast<bool>(std::getline(std::cin, resume)),
                                      "cancelled");
            });
        std::cout << aslice::core::Json{{"bytes", bytes}}.dump() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
