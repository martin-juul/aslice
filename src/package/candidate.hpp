#ifndef ASLICE_PACKAGE_CANDIDATE_HPP
#define ASLICE_PACKAGE_CANDIDATE_HPP
#include "core/result.hpp"
#include "package/version.hpp"
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
using Dependencies = std::map<std::string, Constraint>;
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
                                          std::string artifact);
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

  private:
    Candidate(Identity identity, std::string release, Target target, Dependencies dependencies,
              std::set<std::string> paths, std::string artifact)
        : identity_(std::move(identity)), release_(std::move(release)),
          artifact_(std::move(artifact)), target_(std::move(target)),
          dependencies_(std::move(dependencies)), paths_(std::move(paths)) {}
    Identity identity_;
    std::string release_;
    std::string artifact_;
    Target target_;
    Dependencies dependencies_;
    std::set<std::string> paths_;
};
using Selection = std::map<std::string, Candidate>;
} // namespace aslice::package

#endif // ASLICE_PACKAGE_CANDIDATE_HPP
