#include "cli/registry.hpp"
#include "core/support.hpp"
#include "schemas.hpp"
#include <cstddef>
#include <cstdint>

#include <algorithm>
#include <exception>
#include <iostream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace aslice::cli {
namespace {
enum class Availability : std::uint8_t { portable, posix };
struct Option {
    std::string name;
    std::string value;
    std::string description;
    bool required = false;
};
struct Command {
    std::string path;
    std::string description;
    std::string arguments;
    std::size_t minimum;
    std::size_t maximum;
    std::vector<Option> options;
    std::string example;
    std::string limits;
    Availability availability;
    int (*handler)(const Invocation&);
};
int schema(const Invocation& invocation) {
    const auto role = invocation.option("--role", "client-state");
    for (const auto& entry : schemas) {
        if (entry.role == role) {
            std::cout << entry.sql;
            return 0;
        }
    }
    throw core::Error("unknown database role: " + role);
}
const std::vector<Command>& registry() {
    static const auto commands = [] {
        const Option catalog{"--catalog", "FILE", "Read an unsigned inline-payload catalog.", true};
        const Option prefix{"--prefix", "PATH", "Select a disposable prefix explicitly.", true};
        const Option os{"--target-os", "OS", "Simulate macOS 10.11 through 12 (default: 10.11)."};
        const Option flavor{"--flavor", "FLAVOR", "Select v1, v2, or v3 (default: v1)."};
        const Option dry{"--dry-run", "", "Show the result without committing a generation."};
        const std::string unsigned_limit =
            "Unsigned fixture data cannot authorize production installation.";
        const std::string artifact_limit =
            "Local inspection checks content and identity. It does not authenticate a repository "
            "or authorize installation.";
        std::vector<Command> result{
            {"db schema",
             "Print a shipped database schema.",
             "",
             0,
             0,
             {{"--role", "ROLE",
               "Choose client-state (default), client-cache, system-state, coordinator, publisher, "
               "or release-signer."}},
             "db schema --role client-state",
             "No database is opened or created. Live schemas are unavailable.",
             Availability::portable,
             schema},
            {"version normalize",
             "Normalize an upstream package version.",
             "VALUE",
             1,
             1,
             {},
             "version normalize v7.1",
             "Unsupported version spellings are refused.",
             Availability::portable,
             inspect},
            {"version compare",
             "Compare two normalized package versions.",
             "A B",
             2,
             2,
             {},
             "version compare 1.1.1.11 1.1.1",
             "Prints order -1, 0, or 1.",
             Availability::portable,
             inspect},
            {"version matches",
             "Test a normalized version against a constraint.",
             "VALUE CONSTRAINT",
             2,
             2,
             {},
             "version matches 1.6.43 \">=1.6, <1.7\"",
             "Quote constraints so the shell passes them unchanged.",
             Availability::portable,
             inspect},
            {"artifact inspect",
             "Inspect a manifest and compute its canonical identity.",
             "MANIFEST",
             1,
             1,
             {},
             "artifact inspect manifest.json",
             artifact_limit,
             Availability::portable,
             inspect},
            {"artifact verify",
             "Verify a payload directory against its manifest.",
             "MANIFEST",
             1,
             1,
             {{"--payload", "DIRECTORY", "Read the unpacked payload directory.", true}},
             "artifact verify manifest.json --payload payload",
             artifact_limit +
                 " Payloads are limited to 1 GiB. Windows does not verify POSIX modes.",
             Availability::portable,
             inspect},
            {"slice pack",
             "Pack a verified payload into a local slice archive.",
             "MANIFEST PAYLOAD OUTPUT",
             3,
             3,
             {},
             "slice pack manifest.json payload example.slice",
             artifact_limit +
                 " Existing output is never replaced. Limits: 16 MiB compressed, 64 MiB expanded.",
             Availability::portable,
             inspect},
            {"slice inspect",
             "Inspect and verify a compressed slice archive.",
             "FILE",
             1,
             1,
             {},
             "slice inspect example.slice",
             artifact_limit +
                 " Limits: 16 MiB compressed, 64 MiB expanded; supported ustar subset only.",
             Availability::portable,
             inspect},
            {"dev fixture resolve",
             "Resolve packages from an unsigned fixture catalog.",
             "PACKAGE...",
             1,
             std::numeric_limits<std::size_t>::max(),
             {catalog, os, flavor, {"--prerelease", "", "Admit prerelease candidates."}},
             "dev fixture resolve --catalog catalog.json hello",
             unsigned_limit + " Limits: 128 packages and 10,000 search steps.",
             Availability::portable,
             inspect}};
        const std::vector<std::pair<std::string, std::string>> lifecycle{
            {"init", "Create a new disposable prefix."},
            {"search", "Find fixture package names containing text."},
            {"info", "Show a fixture package from a catalog."},
            {"plan", "Show the resolved installation without committing it."},
            {"install", "Install unsigned fixtures into a disposable prefix."},
            {"list", "List the active generation's packages."},
            {"upgrade", "Resolve the requested packages using newer fixture candidates."},
            {"uninstall", "Remove packages if their dependents permit it."},
            {"autoremove", "Remove packages no longer reachable from requested roots."},
            {"history", "Show retained generations."},
            {"rollback", "Verify and activate a retained generation."},
            {"why", "Show a package's roots and direct dependents."},
            {"leaves", "List installed packages with no dependents."},
            {"verify", "Verify active generation links and stored payloads."}};
        for (const auto& [name, description] : lifecycle) {
            const bool many = name == "install" || name == "plan" || name == "uninstall";
            const bool one =
                name == "info" || name == "why" || name == "search" || name == "rollback";
            std::vector<Option> options{prefix};
            // Catalogs may be passed by a shared fixture invocation wrapper.
            auto catalog_option = catalog;
            catalog_option.required = name == "search" || name == "info" || name == "plan" ||
                                      name == "install" || name == "upgrade";
            options.push_back(catalog_option);
            if (name == "init") {
                options.push_back(os);
                options.push_back(flavor);
            }
            if (many || name == "upgrade" || name == "autoremove" || name == "rollback") {
                options.push_back(dry);
            }
            const std::string argument = name == "rollback" ? "GENERATION"
                                         : name == "search" ? "TEXT"
                                         : many             ? "PACKAGE..."
                                         : one              ? "PACKAGE"
                                                            : "";
            const auto example = "dev fixture " + name + " --prefix /tmp/aslice-play" +
                                 (catalog_option.required ? " --catalog catalog.json" : "") +
                                 (one || many ? (name == "rollback" ? " 1" : " hello") : "");
            result.push_back({"dev fixture " + name, description, argument, one || many ? 1U : 0U,
                              many  ? std::numeric_limits<std::size_t>::max()
                              : one ? 1U
                                    : 0U,
                              std::move(options), example, unsigned_limit, Availability::posix,
                              fixture});
        }
        return result;
    }();
    return commands;
}
bool available(const Command& command) {
#ifdef _WIN32
    return command.availability == Availability::portable;
#else
    (void)command;
    return true;
#endif
}
const Command* find_command(const std::string& path) {
    for (const auto& command : registry()) {
        if (command.path == path) {
            return &command;
        }
    }
    return nullptr;
}
bool group(const std::string& path) {
    return path.empty() ||
           std::any_of(registry().begin(), registry().end(), [&](const auto& command) {
               return command.path.starts_with(path + ' ');
           });
}
void help(const std::string& path) {
    if (const auto* command = find_command(path)) {
        std::cout << command->description << "\n\nUsage: aslice " << path;
        if (!command->arguments.empty()) {
            std::cout << ' ' << command->arguments;
        }
        for (const auto& option : command->options) {
            std::cout << ' ' << (option.required ? "" : "[") << option.name;
            if (!option.value.empty()) {
                std::cout << ' ' << option.value;
            }
            std::cout << (option.required ? "" : "]");
        }
        std::cout << "\n\nExample:\n  aslice " << command->example
                  << "\n\nOptions:\n  --help  Show this page without running the command.\n";
        for (const auto& option : command->options) {
            std::cout << "  " << option.name << ' ' << option.value << "  " << option.description
                      << '\n';
        }
        std::cout << "\n"
                  << command->limits << "\nPlatform: "
                  << (command->availability == Availability::portable
                          ? "Windows, Linux, macOS."
                          : "POSIX (Linux or macOS); use Docker or WSL on Windows.")
                  << '\n';
        return;
    }
    core::require(group(path), "unknown command path: " + path);
    if (path.empty()) {
        std::cout
            << "aslice " ASLICE_VERSION
               "\nInspect package artifacts and exercise disposable fixture prefixes.\n\n"
               "Usage: aslice <command> [arguments]\n\n"
               "  db schema          Print a shipped SQL schema.\n"
               "  version            Normalize, compare, or match package versions.\n"
               "  artifact           Inspect manifests and verify payloads.\n"
               "  slice              Pack or inspect local archives.\n"
               "  dev fixture        Resolve and install unsigned development fixtures.\n\n"
               "Try: aslice artifact inspect manifest.json\n"
               "Use 'aslice help <command path>' for options and examples.\n"
               "--version prints the build version. Production installation is unavailable.\n";
    } else {
        std::cout << "Usage: aslice " << path << " <command>\n\n";
        for (const auto& command : registry()) {
            if (command.path.starts_with(path + ' ')) {
                std::cout << "  " << command.path.substr(path.size() + 1) << "  "
                          << command.description
                          << (available(command) ? "" : " [unavailable on Windows]") << '\n';
            }
        }
        std::cout << "\nUse 'aslice help " << path << " <command>' for options and examples.\n";
    }
}
enum class ParsePurpose : std::uint8_t { execution, help };
Invocation parse(const Command& command, const std::vector<std::string>& arguments,
                 ParsePurpose purpose = ParsePurpose::execution) {
    Invocation invocation{command.path, {}, {}};
    for (std::size_t i = 0; i < arguments.size(); ++i) {
        const auto& arg = arguments[i];
        if (!arg.starts_with("--")) {
            invocation.arguments.push_back(arg);
            continue;
        }
        const auto option = std::find_if(command.options.begin(), command.options.end(),
                                         [&](const auto& candidate) {
                                             return candidate.name == arg;
                                         });
        core::require(option != command.options.end(), "unknown option: " + arg);
        core::require(!invocation.options.contains(arg), "duplicate option: " + arg);
        std::string value;
        if (!option->value.empty()) {
            core::require(++i < arguments.size() && !arguments[i].empty() &&
                              !arguments[i].starts_with("--"),
                          arg + " requires " + option->value);
            value = arguments[i];
        }
        invocation.options.emplace(arg, std::move(value));
    }
    if (purpose == ParsePurpose::help) {
        return invocation;
    }
    core::require(invocation.arguments.size() >= command.minimum &&
                      invocation.arguments.size() <= command.maximum,
                  "expected arguments: " + command.arguments);
    for (const auto& option : command.options) {
        core::require(!option.required || invocation.options.contains(option.name),
                      "required option: " + option.name);
    }
    return invocation;
}
} // namespace
std::string Invocation::option(const std::string& name, const std::string& fallback) const {
    const auto found = options.find(name);
    return found == options.end() ? fallback : found->second;
}
int dispatch(int argc, char** argv) {
    std::string path;
    try {
        std::vector<std::string> words;
        for (int i = 1; i < argc; ++i) {
            words.emplace_back(argv[i]);
        }
        if (words == std::vector<std::string>{"--version"}) {
            std::cout << "aslice " ASLICE_VERSION "\n";
        } else {
            bool wants_help = words.empty();
            if (!words.empty() && words.front() == "help") {
                wants_help = true;
                words.erase(words.begin());
            }
            const auto help_option = std::find(words.begin(), words.end(), "--help");
            if (help_option != words.end()) {
                wants_help = true;
                words.erase(help_option);
            }
            std::size_t consumed = 0;
            std::vector<std::string> arguments;
            while (consumed < words.size() && !find_command(path)) {
                if (!path.empty() && words[consumed].starts_with("--")) {
                    const Option* selected = nullptr;
                    for (const auto& candidate : registry()) {
                        if (!candidate.path.starts_with(path + ' ')) {
                            continue;
                        }
                        for (const auto& option : candidate.options) {
                            if (option.name == words[consumed]) {
                                selected = &option;
                                break;
                            }
                        }
                        if (selected) {
                            break;
                        }
                    }
                    core::require(selected != nullptr, "unknown option: " + words[consumed]);
                    arguments.push_back(words[consumed++]);
                    if (!selected->value.empty()) {
                        core::require(consumed < words.size() && !words[consumed].empty() &&
                                          !words[consumed].starts_with("--"),
                                      selected->name + " requires " + selected->value);
                        arguments.push_back(words[consumed++]);
                    }
                    continue;
                }
                const auto next = path.empty() ? words[consumed] : path + ' ' + words[consumed];
                core::require(find_command(next) || group(next), "unknown command: " + next);
                path = next;
                ++consumed;
            }
            arguments.insert(arguments.end(), words.begin() + static_cast<std::ptrdiff_t>(consumed),
                             words.end());
            if (wants_help || group(path)) {
                if (const auto* command = find_command(path)) {
                    parse(*command, arguments, ParsePurpose::help);
                }
                help(path);
            } else {
                const auto* command = find_command(path);
                core::require(command != nullptr, "unknown command");
                const auto invocation = parse(*command, arguments);
                core::require(
                    available(*command),
                    "unavailable on Windows; use Docker or WSL for POSIX fixture operations");
                const auto status = command->handler(invocation);
                std::cout.flush();
                if (!std::cout) {
                    throw core::Error("cannot write output", "io");
                }
                return status;
            }
        }
        std::cout.flush();
        if (!std::cout) {
            throw core::Error("cannot write output", "io");
        }
        return 0;
    } catch (const core::Error& error) {
        std::cerr << "aslice: " << error.what() << "; run 'aslice"
                  << (path.empty() ? "" : " " + path) << " --help' for usage.\n";
        return error.code == "io" ? 1 : error.code == "busy" ? 4 : 2;
    } catch (const std::exception& error) {
        std::cerr << "aslice: " << error.what() << '\n';
        return 2;
    }
}
} // namespace aslice::cli
