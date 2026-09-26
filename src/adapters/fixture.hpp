#ifndef ASLICE_ADAPTERS_FIXTURE_HPP
#define ASLICE_ADAPTERS_FIXTURE_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include "package/candidate.hpp"
#include "resolver/solver.hpp"
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>
namespace aslice::adapters::fixture {
inline constexpr auto format = "aslice-prototype-1";
struct InlineFile {
    std::string text;
    bool executable;
};
using InlineFiles = std::map<std::string, InlineFile>;
class Package {
  public:
    static core::Result<Package> parse(core::Json value);
    const package::Candidate& candidate() const {
        return candidate_;
    }
    const core::Json& document() const {
        return document_;
    }
    const InlineFiles& files() const {
        return files_;
    }

  private:
    Package(core::Json document, package::Candidate candidate, InlineFiles files)
        : document_(std::move(document)), candidate_(std::move(candidate)),
          files_(std::move(files)) {}
    core::Json document_;
    package::Candidate candidate_;
    InlineFiles files_;
};
using Selection = std::map<std::string, Package>;

class Generation {
  public:
    static core::Result<Generation> parse(const core::Json& document,
                                          const std::string& expected_id);
    const std::string& id() const {
        return id_;
    }
    const std::string& parent() const {
        return parent_;
    }
    const Selection& selected() const {
        return selected_;
    }
    const std::set<std::string>& roots() const {
        return roots_;
    }

  private:
    Generation(std::string id, std::string parent, Selection selected, std::set<std::string> roots)
        : id_(std::move(id)), parent_(std::move(parent)), selected_(std::move(selected)),
          roots_(std::move(roots)) {}
    std::string id_;
    std::string parent_;
    Selection selected_;
    std::set<std::string> roots_;
};
core::Json generation_document(const std::string& id, const std::string& parent,
                               const Selection& selected, const std::set<std::string>& roots);
core::Result<Selection> selection(const core::Json& value);
core::Json serialize(const Selection& selected);
core::Result<std::set<std::string>> requested(const core::Json& document);
core::Json summary(const Selection& selected, const std::set<std::string>& roots);
core::Result<std::vector<Package>> catalog(const core::Json& document);
package::Selection candidates(const Selection& selected);
core::Result<Selection>
resolve(const std::vector<Package>& packages, const std::set<std::string>& roots,
        const Selection& installed, resolver::Preference preference, const package::Target& target,
        package::PrereleasePolicy prereleases = package::PrereleasePolicy::normal);
} // namespace aslice::adapters::fixture

#endif // ASLICE_ADAPTERS_FIXTURE_HPP
