#ifndef ASLICE_DB_QUERY_HPP
#define ASLICE_DB_QUERY_HPP
#include "core/result.hpp"
#include <chrono>
#include <cstddef>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
struct sqlite3;
namespace aslice::db {
struct Identity {
    std::string role;
    std::string instance;
    std::string owner;
};
struct QueryLimits {
    std::size_t rows = 10000;
    std::size_t output_bytes = 16 * 1024 * 1024;
    std::chrono::milliseconds timeout{5000};
};
// Caller supplies an owner-approved standalone snapshot and independent identity.
// Use a dedicated inspection process: SQLite's heap ceiling is process-wide.
class Snapshot {
  public:
    static core::Result<Snapshot> create(std::span<const std::byte> bytes,
                                         const Identity& expected);
    Snapshot(Snapshot&&) noexcept;
    Snapshot& operator=(Snapshot&&) noexcept;
    ~Snapshot();
    Snapshot(const Snapshot&) = delete;
    Snapshot& operator=(const Snapshot&) = delete;
    // Returns the JSON data object, not a command envelope. Never returns partial rows.
    core::Result<std::string> query(std::string_view sql, QueryLimits limits = {});

  private:
    Snapshot(std::span<const std::byte> bytes, const Identity& expected);
    std::string query_impl(std::string_view sql, QueryLimits limits);
    struct Close {
        void operator()(sqlite3*) const;
    };
    std::unique_ptr<sqlite3, Close> db_;
};
} // namespace aslice::db

#endif // ASLICE_DB_QUERY_HPP
