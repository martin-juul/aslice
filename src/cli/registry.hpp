#ifndef ASLICE_CLI_REGISTRY_HPP
#define ASLICE_CLI_REGISTRY_HPP

#include "platform/target_filesystem.hpp"
#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::cli {
struct Invocation {
    std::string command;
    std::vector<std::string> arguments;
    std::map<std::string, std::string> options;
    platform::FileSystem& filesystem;
    std::string option(const std::string& name, const std::string& fallback = {}) const;
};
int dispatch(int argc, char** argv, platform::FileSystem& filesystem);
int inspect(const Invocation& invocation);
int fixture(const Invocation& invocation);
} // namespace aslice::cli

#endif // ASLICE_CLI_REGISTRY_HPP
