#include "package/version.hpp"
#include "core/result.hpp"
#include "core/support.hpp"
#include <algorithm>
#include <charconv>
#include <compare>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace aslice::package {
namespace {
using core::require;
bool digits(std::string_view s) {
    return !s.empty() && s.find_first_not_of("0123456789") == s.npos;
}
enum class NumberSpelling : std::uint8_t { canonical, upstream };
std::uint64_t number(std::string_view text, NumberSpelling spelling) {
    require(digits(text) &&
                (spelling == NumberSpelling::upstream || text.size() == 1 || text.front() != '0'),
            "invalid version number");
    std::uint64_t result = 0;
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), result);
    require(parsed.ec == std::errc{}, "version number overflow");
    return result;
}
// Returned token views borrow text; the caller keeps its input alive while using them.
std::vector<std::string_view> split(std::string_view text, std::string_view separator) {
    std::vector<std::string_view> result;
    for (;;) {
        const auto at = text.find(separator);
        result.push_back(text.substr(0, at));
        if (at == text.npos) {
            return result;
        }
        text.remove_prefix(at + separator.size());
    }
}
std::string_view trim(std::string_view text) {
    const auto begin = text.find_first_not_of(" \t");
    if (begin == text.npos) {
        return {};
    }
    return text.substr(begin, text.find_last_not_of(" \t") - begin + 1);
}
} // namespace

Version Version::parse_impl(std::string_view text) {
    require(!text.empty() && text.size() <= 256, "invalid version length");
    Version result;
    if (const auto at = text.find('!'); at != text.npos) {
        result.epoch_ = number(text.substr(0, at), NumberSpelling::canonical);
        text.remove_prefix(at + 1);
    }
    const auto dash = text.find('-');
    const auto components = split(text.substr(0, dash), ".");
    require(components.size() == 3 || components.size() == 4,
            "normalized version requires three or four components");
    for (std::size_t i = 0; i < components.size(); ++i) {
        result.parts_[i] = number(components[i], NumberSpelling::canonical);
    }
    result.fourth_ = components.size() == 4;
    if (dash != text.npos) {
        for (auto identifier : split(text.substr(dash + 1), ".")) {
            require(!identifier.empty() &&
                        identifier.find_first_not_of(
                            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-") ==
                            identifier.npos,
                    "invalid prerelease identifier");
            // Numeric prerelease identifiers are compared without a machine integer limit.
            require(!digits(identifier) || identifier.size() == 1 || identifier.front() != '0',
                    "leading zero in prerelease");
            result.pre_.emplace_back(identifier);
        }
    }
    return result;
}

Version Version::normalize_impl(std::string_view text) {
    require(!text.empty() && text.size() <= 256, "invalid upstream version length");
    if (text.front() == 'v') {
        text.remove_prefix(1);
    }
    std::string prefix;
    if (const auto at = text.find('!'); at != text.npos) {
        prefix = std::to_string(number(text.substr(0, at), NumberSpelling::upstream)) + "!";
        text.remove_prefix(at + 1);
    }
    const auto dash = text.find('-');
    auto numeric = text.substr(0, dash);
    unsigned letter = 0;
    if (!numeric.empty() && numeric.back() >= 'a' && numeric.back() <= 'z') {
        letter = static_cast<unsigned>(numeric.back() - 'a' + 1);
        numeric.remove_suffix(1);
    }
    const auto components = split(numeric, ".");
    require(!components.empty() && components.size() <= 4 && (!letter || components.size() == 3),
            "invalid upstream version");
    for (std::size_t i = 0; i < std::max<std::size_t>(3, components.size()); ++i) {
        if (i) {
            prefix += '.';
        }
        prefix += i < components.size()
                      ? std::to_string(number(components[i], NumberSpelling::upstream))
                      : "0";
    }
    if (letter) {
        prefix += "." + std::to_string(letter);
    }
    if (dash != text.npos) {
        prefix += std::string(text.substr(dash));
    }
    return parse_impl(prefix);
}

std::string Version::string() const {
    std::string result = epoch_ ? std::to_string(epoch_) + "!" : "";
    for (std::size_t i = 0; i < (fourth_ ? 4u : 3u); ++i) {
        if (i) {
            result += '.';
        }
        result += std::to_string(parts_[i]);
    }
    for (std::size_t i = 0; i < pre_.size(); ++i) {
        result += (i ? "." : "-") + pre_[i];
    }
    return result;
}

std::strong_ordering Version::operator<=>(const Version& other) const {
    if (auto order = epoch_ <=> other.epoch_; order != 0) {
        return order;
    }
    if (auto order = parts_ <=> other.parts_; order != 0) {
        return order;
    }
    if (pre_.empty() != other.pre_.empty()) {
        return pre_.empty() ? std::strong_ordering::greater : std::strong_ordering::less;
    }
    for (std::size_t i = 0; i < std::min(pre_.size(), other.pre_.size()); ++i) {
        const auto& a = pre_[i];
        const auto& b = other.pre_[i];
        const bool an = digits(a);
        const bool bn = digits(b);
        if (an != bn) {
            return an ? std::strong_ordering::less : std::strong_ordering::greater;
        }
        if (an && a.size() != b.size()) {
            return a.size() <=> b.size();
        }
        if (auto order = a <=> b; order != 0) {
            return order;
        }
    }
    return pre_.size() <=> other.pre_.size();
}
bool Version::operator==(const Version& other) const {
    return (*this <=> other) == 0;
}

Constraint Constraint::parse_impl(std::string_view text) {
    require(text.size() <= 4096, "constraint too long");
    Constraint result;
    for (auto alternative : split(text, "||")) {
        Intersection terms;
        for (auto raw : split(alternative, ",")) {
            auto token = trim(raw);
            require(!token.empty(), "empty version constraint");
            if (token == "*") {
                continue;
            }
            const bool caret = token.front() == '^';
            const bool tilde = token.front() == '~';
            Op op = Op::equal;
            if (token.starts_with(">=")) {
                op = Op::greater_equal;
                token.remove_prefix(2);
            } else if (token.starts_with("<=")) {
                op = Op::less_equal;
                token.remove_prefix(2);
            } else if (token.front() == '>') {
                op = Op::greater;
                token.remove_prefix(1);
            } else if (token.front() == '<') {
                op = Op::less;
                token.remove_prefix(1);
            } else if (token.front() == '=' || caret || tilde) {
                token.remove_prefix(1);
            } else {
                throw core::Error("constraint requires *, =, <, <=, >, >=, ^, or ~");
            }
            token = trim(token);
            // Constraint bounds may omit trailing components, but are not upstream tags.
            require(!token.empty() && token.front() != 'v' && token.find('+') == token.npos,
                    "invalid constraint bound");
            const auto end = token.find('-');
            const auto epoch = token.find('!');
            if (epoch != token.npos) {
                (void)number(token.substr(0, epoch), NumberSpelling::canonical);
            }
            auto numeric = token.substr(
                epoch == token.npos ? 0 : epoch + 1,
                end == token.npos ? token.npos : end - (epoch == token.npos ? 0 : epoch + 1));
            const auto parts = split(numeric, ".");
            for (auto part : parts) {
                (void)number(part, NumberSpelling::canonical);
            }
            auto bound = aslice::core::take(Version::normalize(token));
            terms.push_back({caret || tilde ? Op::greater_equal : op, bound});
            if (caret || tilde) {
                std::size_t pivot = tilde ? (parts.size() == 1 ? 0 : 1) : 0;
                if (caret) {
                    while (pivot + 1 < std::min<std::size_t>(3, parts.size()) &&
                           bound.parts_[pivot] == 0) {
                        ++pivot;
                    }
                }
                require(bound.parts_[pivot] != std::numeric_limits<std::uint64_t>::max(),
                        "constraint upper bound overflow");
                ++bound.parts_[pivot];
                for (std::size_t i = pivot + 1; i < 4; ++i) {
                    bound.parts_[i] = 0;
                }
                bound.pre_.clear();
                bound.fourth_ = false;
                terms.push_back({Op::less, bound});
            }
        }
        result.alternatives_.push_back(std::move(terms));
    }
    return result;
}

bool Constraint::matches(const Version& value, PrereleasePolicy prereleases) const {
    for (const auto& terms : alternatives_) {
        bool explicit_pre = false;
        bool matched = true;
        for (const auto& term : terms) {
            explicit_pre |= term.bound.prerelease() && term.bound.epoch_ == value.epoch_ &&
                            term.bound.parts_ == value.parts_;
            const auto order = value <=> term.bound;
            switch (term.op) {
            case Op::equal:
                matched &= order == 0;
                break;
            case Op::less:
                matched &= order < 0;
                break;
            case Op::less_equal:
                matched &= order <= 0;
                break;
            case Op::greater:
                matched &= order > 0;
                break;
            case Op::greater_equal:
                matched &= order >= 0;
                break;
            }
        }
        if (matched &&
            (!value.prerelease() || prereleases == PrereleasePolicy::allow || explicit_pre)) {
            return true;
        }
    }
    return false;
}

core::Result<Version> Version::parse(std::string_view text) {
    return core::capture([&] {
        return Version::parse_impl(text);
    });
}

core::Result<Version> Version::normalize(std::string_view upstream) {
    return core::capture([&] {
        return Version::normalize_impl(upstream);
    });
}

core::Result<Constraint> Constraint::parse(std::string_view text) {
    return core::capture([&] {
        return Constraint::parse_impl(text);
    });
}
} // namespace aslice::package
