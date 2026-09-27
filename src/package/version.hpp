#ifndef ASLICE_PACKAGE_VERSION_HPP
#define ASLICE_PACKAGE_VERSION_HPP
#include "core/result.hpp"
#include <array>
#include <compare>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace aslice::package {
enum class PrereleasePolicy : std::uint8_t { normal, allow };
// PACKAGE-FORMAT 4: normalized SemVer with epoch and an optional patch4.
class Version {
  public:
    static core::Result<Version> parse(std::string_view text);
    static core::Result<Version> normalize(std::string_view upstream);
    std::string string() const;
    bool prerelease() const {
        return !pre_.empty();
    }
    std::strong_ordering operator<=>(const Version& other) const;
    bool operator==(const Version& other) const;

  private:
    Version() = default;
    static Version normalize_impl(std::string_view upstream);
    static Version parse_impl(std::string_view text);
    std::uint64_t epoch_ = 0;
    std::array<std::uint64_t, 4> parts_{};
    bool fourth_ = false;
    std::vector<std::string> pre_;
    friend class Constraint;
};

class Constraint {
  public:
    static core::Result<Constraint> parse(std::string_view text);
    bool matches(const Version& version,
                 PrereleasePolicy prereleases = PrereleasePolicy::normal) const;

  private:
    Constraint() = default;
    static Constraint parse_impl(std::string_view text);
    enum class Op : std::uint8_t { equal, less, less_equal, greater, greater_equal };
    struct Term {
        Op op;
        Version bound;
    };
    using Intersection = std::vector<Term>;
    std::vector<Intersection> alternatives_;
};
} // namespace aslice::package

#endif // ASLICE_PACKAGE_VERSION_HPP
