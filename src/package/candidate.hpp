#ifndef ASLICE_PACKAGE_CANDIDATE_HPP
#define ASLICE_PACKAGE_CANDIDATE_HPP
#include "core/result.hpp"
#include "package/version.hpp"
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace aslice::package {
core::Result<std::string> key(std::string value);
core::Result<Version> version(const std::string& value);
core::Result<bool> satisfies(const std::string& value, const std::string& constraint);
core::Result<int> os_rank(const std::string& value);
core::Result<int> flavor_rank(const std::string& value);
class Target {
  public:
    static core::Result<Target> create(std::string os, std::string flavor);
    const std::string& os() const {
        return os_;
    }
    const std::string& flavor() const {
        return flavor_;
    }

  private:
    Target(std::string os, std::string flavor) : os_(std::move(os)), flavor_(std::move(flavor)) {}
    std::string os_;
    std::string flavor_;
};
using Variants = std::map<std::string, bool>;
class Dependency {
  public:
    static core::Result<Dependency> parse(const std::string& text);
    const Constraint& constraint() const {
        return constraint_;
    }
    bool accepts(const Variants& variants) const;

  private:
    Dependency(Constraint constraint, std::set<std::string> required)
        : constraint_(std::move(constraint)), required_(std::move(required)) {}
    Constraint constraint_;
    std::set<std::string> required_;
};
using Dependencies = std::map<std::string, Dependency>;
class Identity {
  public:
    static core::Result<Identity> parse(std::string name);
    const std::string& string() const {
        return name_;
    }

  private:
    explicit Identity(std::string name) : name_(std::move(name)) {}
    std::string name_;
};
class Candidate {
  public:
    static core::Result<Candidate> create(std::string name, std::string release, Target target,
                                          Dependencies dependencies, std::set<std::string> paths,
                                          std::string artifact, Variants variants = {},
                                          std::uint64_t revision = 0);
    const std::string& name() const {
        return identity_.string();
    }
    const std::string& release() const {
        return release_;
    }
    const std::string& artifact() const {
        return artifact_;
    }
    const Target& target() const {
        return target_;
    }
    const Dependencies& dependencies() const {
        return dependencies_;
    }
    const std::set<std::string>& paths() const {
        return paths_;
    }
    const Variants& variants() const {
        return variants_;
    }
    std::uint64_t revision() const {
        return revision_;
    }

  private:
    Candidate(Identity identity, std::string release, Target target, Dependencies dependencies,
              std::set<std::string> paths, std::string artifact, Variants variants,
              std::uint64_t revision)
        : identity_(std::move(identity)), release_(std::move(release)),
          artifact_(std::move(artifact)), target_(std::move(target)),
          dependencies_(std::move(dependencies)), paths_(std::move(paths)),
          variants_(std::move(variants)), revision_(revision) {}
    Identity identity_;
    std::string release_;
    std::string artifact_;
    Target target_;
    Dependencies dependencies_;
    std::set<std::string> paths_;
    Variants variants_;
    std::uint64_t revision_;
};
using Selection = std::map<std::string, Candidate>;
} // namespace aslice::package

#endif // ASLICE_PACKAGE_CANDIDATE_HPP
