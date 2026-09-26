#ifndef ASLICE_CORE_SUPPORT_HPP
#define ASLICE_CORE_SUPPORT_HPP
#include "core/result.hpp"
#include <filesystem>
#include <nlohmann/json.hpp>
#include <set>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>

namespace aslice::core {
using Json = nlohmann::json;
namespace fs = std::filesystem;
// Internal validation unwinding is translated to Result at each public boundary.
struct Error : std::runtime_error {
    std::string code;
    explicit Error(const std::string& message, std::string kind = "invalid")
        : std::runtime_error(message), code(std::move(kind)) {}
};
template <class T> T take(Result<T> result) {
    if (!result) {
        throw Error(result.error().message, result.error().code);
    }
    if constexpr (!std::is_void_v<T>) {
        return std::move(*result);
    }
}
template <class Operation>
auto capture(Operation&& operation) -> Result<std::invoke_result_t<Operation>> {
    using Value = std::invoke_result_t<Operation>;
    try {
        if constexpr (std::is_void_v<Value>) {
            operation();
            return {};
        } else {
            return operation();
        }
    } catch (const Error& error) {
        return tl::unexpected(Failure{error.code, error.what()});
    } catch (const std::exception& error) {
        return tl::unexpected(Failure{"invalid", error.what()});
    }
}
void require(bool condition, const std::string& message);
core::Result<std::string> digest(const std::string& bytes);
core::Result<void> fields(const Json& object, const std::set<std::string>& allowed);
core::Result<std::string> read_bytes(const fs::path& path, std::size_t maximum = 4 * 1024 * 1024);
core::Result<Json> read_json(const fs::path& path);
core::Result<Json> parse_json(const std::string& bytes);
core::Result<void> no_symlinks(const fs::path& path);

} // namespace aslice::core

#endif // ASLICE_CORE_SUPPORT_HPP
