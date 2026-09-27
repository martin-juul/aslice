#ifndef ASLICE_CORE_RESULT_HPP
#define ASLICE_CORE_RESULT_HPP
#include <string>
#include <tl/expected.hpp>
#include <utility>

namespace aslice::core {
struct Failure {
    std::string code;
    std::string message;
};
template <class T> using Result = tl::expected<T, Failure>;
} // namespace aslice::core

#endif // ASLICE_CORE_RESULT_HPP
