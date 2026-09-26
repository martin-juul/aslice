#ifndef ASLICE_PACKAGE_MANIFEST_HPP
#define ASLICE_PACKAGE_MANIFEST_HPP
#include "core/result.hpp"
#include "core/support.hpp"
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace aslice::package {
// Local inspection only: a digest is an identity, never repository authorization.
struct InventoryEntry {
    std::string path;
    std::string kind;
    unsigned mode;
    std::uint64_t size;
    std::string sha256;
    std::string target;
};
struct Relocation {
    std::string path;
    std::size_t offset;
    std::string expected_hex;
};
class Manifest {
  public:
    static core::Result<Manifest> parse(core::Json value);
    const std::vector<InventoryEntry>& inventory() const {
        return inventory_;
    }
    const std::vector<Relocation>& relocations() const {
        return relocations_;
    }
    const std::string& canonical() const {
        return canonical_;
    }
    const std::string& artifact_id() const {
        return artifact_id_;
    }
    std::uint64_t payload_bytes() const {
        return payload_bytes_;
    }
    core::Json inspect() const;
    core::Result<core::Json> verify_payload(const core::fs::path& root) const;

  private:
    core::Json verify_payload_impl(const core::fs::path& input) const;
    core::Json document_;
    std::vector<InventoryEntry> inventory_;
    std::vector<Relocation> relocations_;
    std::string canonical_;
    std::string artifact_id_;
    std::uint64_t payload_bytes_ = 0;
    explicit Manifest(core::Json value);
};
} // namespace aslice::package

#endif // ASLICE_PACKAGE_MANIFEST_HPP
