#include "query.hpp"
#include "core/result.hpp"
#include "tl/expected.hpp"
#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <exception>
#include <memory>
#include <span>
#include <sqlite3.h>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

namespace aslice::db {
struct QueryError : std::runtime_error {
    std::string code;
    QueryError(std::string code, const std::string& message);
};

namespace {
constexpr std::size_t mib = 1024 * 1024;
using Clock = std::chrono::steady_clock;
using Statement = std::unique_ptr<sqlite3_stmt, decltype(&sqlite3_finalize)>;
[[noreturn]] void fail(std::string code, const std::string& message) {
    throw QueryError(std::move(code), message);
}
void check(int rc, sqlite3* db) {
    if (rc == SQLITE_OK || rc == SQLITE_DONE || rc == SQLITE_ROW) {
        return;
    }
    if (rc == SQLITE_INTERRUPT) {
        fail("query_timeout", "Query exceeded its execution deadline.");
    }
    if (rc == SQLITE_TOOBIG || rc == SQLITE_NOMEM) {
        fail("query_limit", "Query exceeded a resource limit.");
    }
    fail("query_refused", sqlite3_errmsg(db));
}
Statement prepare(sqlite3* db, const char* sql) {
    sqlite3_stmt* raw = nullptr;
    const int rc = sqlite3_prepare_v2(db, sql, -1, &raw, nullptr);
    Statement result(raw, sqlite3_finalize);
    check(rc, db);
    return result;
}
int scalar(sqlite3* db, const char* sql) {
    auto stmt = prepare(db, sql);
    if (sqlite3_step(stmt.get()) != SQLITE_ROW) {
        fail("identity_mismatch", "Missing database header.");
    }
    return sqlite3_column_int(stmt.get(), 0);
}
// Borrowed SQLite text remains valid until the statement steps, resets, or finalizes.
std::string_view text(sqlite3_stmt* stmt, int column) {
    const auto* data = sqlite3_column_text(stmt, column);
    const auto size = sqlite3_column_bytes(stmt, column);
    return {data ? reinterpret_cast<const char*>(data) : "", static_cast<std::size_t>(size)};
}
// Encode UTF-8 as ASCII JSON. Invalid UTF-8 refuses rather than losing bytes.
std::string quote(std::string_view value, std::size_t maximum = 16 * mib) {
    constexpr char hex[] = "0123456789abcdef";
    std::string out = "\"";
    auto escape = [&](unsigned cp) {
        out += "\\u";
        for (int shift = 12; shift >= 0; shift -= 4) {
            out += hex[(cp >> shift) & 15];
        }
    };
    auto invalid = [] {
        fail("invalid_text", "Invalid UTF-8 text; select it as a BLOB.");
    };
    for (std::size_t i = 0; i < value.size();) {
        if (out.size() >= maximum) {
            fail("query_limit", "Query output exceeds its byte limit.");
        }
        const auto c = static_cast<unsigned char>(value[i++]);
        if (c < 128) {
            if (c == '"' || c == '\\') {
                out += '\\';
                out += static_cast<char>(c);
            } else if (c < 32) {
                escape(c);
            } else {
                out += static_cast<char>(c);
            }
            continue;
        }
        unsigned cp = 0;
        unsigned count = 0;
        unsigned minimum = 0;
        if (c >= 0xc2 && c <= 0xdf) {
            cp = c & 31;
            count = 1;
            minimum = 0x80;
        } else if (c >= 0xe0 && c <= 0xef) {
            cp = c & 15;
            count = 2;
            minimum = 0x800;
        } else if (c >= 0xf0 && c <= 0xf4) {
            cp = c & 7;
            count = 3;
            minimum = 0x10000;
        } else {
            invalid();
        }
        for (unsigned j = 0; j < count; ++j) {
            if (i == value.size() || (static_cast<unsigned char>(value[i]) & 0xc0) != 0x80) {
                invalid();
            }
            cp = (cp << 6) | (static_cast<unsigned char>(value[i++]) & 63);
        }
        if (cp < minimum || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) {
            invalid();
        }
        if (cp <= 0xffff) {
            escape(cp);
        } else {
            cp -= 0x10000;
            escape(0xd800 + (cp >> 10));
            escape(0xdc00 + (cp & 1023));
        }
    }
    if (out.size() >= maximum) {
        fail("query_limit", "Query output exceeds its byte limit.");
    }
    return out + '"';
}
std::string cell(sqlite3_stmt* stmt, int column, std::size_t maximum) {
    switch (sqlite3_column_type(stmt, column)) {
    case SQLITE_NULL:
        return "null";
    case SQLITE_INTEGER: {
        const auto number = sqlite3_column_int64(stmt, column);
        auto value = std::to_string(number);
        return number < -9007199254740991LL || number > 9007199254740991LL ? quote(value) : value;
    }
    case SQLITE_FLOAT: {
        const double number = sqlite3_column_double(stmt, column);
        if (!std::isfinite(number)) {
            fail("invalid_number", "Non-finite numbers cannot be represented as JSON.");
        }
        std::array<char, 64> buffer{};
        const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), number);
        if (result.ec != std::errc{}) {
            fail("invalid_number", "Cannot format number.");
        }
        return {buffer.data(), result.ptr};
    }
    case SQLITE_TEXT:
        return quote(text(stmt, column), maximum);
    case SQLITE_BLOB: {
        constexpr char alphabet[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        const auto* data = static_cast<const unsigned char*>(sqlite3_column_blob(stmt, column));
        const int size = sqlite3_column_bytes(stmt, column);
        if (12 + 4 * ((static_cast<std::size_t>(size) + 2) / 3) > maximum) {
            fail("query_limit", "Query output exceeds its byte limit.");
        }
        std::string out = "{\"bytes\":\"";
        for (int i = 0; i < size; i += 3) {
            const unsigned n = (unsigned(data[i]) << 16) |
                               (i + 1 < size ? unsigned(data[i + 1]) << 8 : 0) |
                               (i + 2 < size ? unsigned(data[i + 2]) : 0);
            out += alphabet[n >> 18];
            out += alphabet[(n >> 12) & 63];
            out += i + 1 < size ? alphabet[(n >> 6) & 63] : '=';
            out += i + 2 < size ? alphabet[n & 63] : '=';
        }
        return out + "\"}";
    }
    default:
        fail("query_error", "Unknown SQLite value type.");
    }
}
int authorize(void*, int action, const char*, const char* function, const char*, const char*) {
    if (action == SQLITE_SELECT || action == SQLITE_READ || action == SQLITE_RECURSIVE) {
        return SQLITE_OK;
    }
    if (action == SQLITE_FUNCTION && function) {
        constexpr std::array allowed = {
            "abs",       "coalesce", "count", "hex",    "ifnull",  "instr", "length", "lower",
            "ltrim",     "max",      "min",   "nullif", "replace", "round", "rtrim",  "substr",
            "substring", "sum",      "total", "trim",   "typeof",  "upper", "like",   "glob"};
        for (const auto* name : allowed) {
            if (sqlite3_stricmp(function, name) == 0) {
                return SQLITE_OK;
            }
        }
    }
    return SQLITE_DENY;
}
bool whitespace(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
}
} // namespace
QueryError::QueryError(std::string value, const std::string& message)
    : std::runtime_error(message), code(std::move(value)) {}
void Snapshot::Close::operator()(sqlite3* db) const {
    sqlite3_close(db);
}
Snapshot::~Snapshot() = default;
Snapshot::Snapshot(Snapshot&&) noexcept = default;
Snapshot& Snapshot::operator=(Snapshot&&) noexcept = default;
core::Result<Snapshot> Snapshot::create(std::span<const std::byte> bytes,
                                        const Identity& expected) {
    try {
        return Snapshot(bytes, expected);
    } catch (const QueryError& error) {
        return tl::unexpected(core::Failure{error.code, error.what()});
    } catch (const std::exception& error) {
        return tl::unexpected(core::Failure{"query_error", error.what()});
    }
}
core::Result<std::string> Snapshot::query(std::string_view sql, QueryLimits limits) {
    try {
        return query_impl(sql, limits);
    } catch (const QueryError& error) {
        return tl::unexpected(core::Failure{error.code, error.what()});
    } catch (const std::exception& error) {
        return tl::unexpected(core::Failure{"query_error", error.what()});
    }
}
Snapshot::Snapshot(std::span<const std::byte> bytes, const Identity& expected) {
    if (bytes.empty() || bytes.size() > 32 * mib) {
        fail("snapshot_limit", "Snapshot must be between 1 byte and 32 MiB.");
    }
    sqlite3_hard_heap_limit64(64 * mib);
    sqlite3* raw = nullptr;
    const int rc = sqlite3_open_v2(
        ":memory:", &raw, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_MEMORY, nullptr);
    db_.reset(raw);
    check(rc, raw);
    auto* copy = static_cast<unsigned char*>(sqlite3_malloc64(bytes.size()));
    if (!copy) {
        fail("query_limit", "Cannot allocate inspection snapshot.");
    }
    std::memcpy(copy, bytes.data(), bytes.size());
    // FREEONCLOSE also frees the buffer when deserialize fails.
    check(sqlite3_deserialize(raw, "main", copy, static_cast<sqlite3_int64>(bytes.size()),
                              static_cast<sqlite3_int64>(bytes.size()),
                              SQLITE_DESERIALIZE_FREEONCLOSE | SQLITE_DESERIALIZE_READONLY),
          raw);
    int enabled = 0;
    check(sqlite3_db_config(raw, SQLITE_DBCONFIG_DEFENSIVE, 1, &enabled), raw);
    if (enabled != 1) {
        fail("query_error", "Cannot enable defensive mode.");
    }
    check(sqlite3_db_config(raw, SQLITE_DBCONFIG_TRUSTED_SCHEMA, 0, &enabled), raw);
    if (enabled != 0) {
        fail("query_error", "Cannot disable trusted schema.");
    }
    check(sqlite3_exec(raw, "PRAGMA query_only=ON; PRAGMA temp_store=MEMORY;", nullptr, nullptr,
                       nullptr),
          raw);
    sqlite3_limit(raw, SQLITE_LIMIT_LENGTH, 16 * mib);
    sqlite3_limit(raw, SQLITE_LIMIT_SQL_LENGTH, 64 * 1024);
    sqlite3_limit(raw, SQLITE_LIMIT_COLUMN, 128);
    sqlite3_limit(raw, SQLITE_LIMIT_EXPR_DEPTH, 100);
    sqlite3_limit(raw, SQLITE_LIMIT_COMPOUND_SELECT, 10);
    sqlite3_limit(raw, SQLITE_LIMIT_VDBE_OP, 25000);
    sqlite3_limit(raw, SQLITE_LIMIT_ATTACHED, 0);
    sqlite3_limit(raw, SQLITE_LIMIT_LIKE_PATTERN_LENGTH, 1024);
    sqlite3_limit(raw, SQLITE_LIMIT_VARIABLE_NUMBER, 128);
    constexpr std::array roles = {"client-state", "client-cache", "system-state",
                                  "coordinator",  "publisher",    "release-signer"};
    const auto role = std::find(roles.begin(), roles.end(), expected.role);
    if (role == roles.end()) {
        fail("identity_mismatch", "Unknown expected role.");
    }
    const int version = expected.role == "client-cache" || expected.role == "coordinator" ? 3 : 2;
    if (scalar(raw, "PRAGMA application_id") != 1095977985 + (role - roles.begin()) ||
        scalar(raw, "PRAGMA user_version") != version) {
        fail("identity_mismatch", "Snapshot application ID or schema version does not match.");
    }
    if (expected.instance.size() != 32 ||
        expected.instance.find_first_not_of("0123456789abcdef") != std::string::npos ||
        expected.owner.empty()) {
        fail("identity_mismatch", "Expected identity is not provisioned.");
    }
    auto kind = prepare(
        raw, "SELECT type FROM pragma_table_list WHERE schema='main' AND name='database_identity'");
    if (sqlite3_step(kind.get()) != SQLITE_ROW || text(kind.get(), 0) != "table" ||
        sqlite3_step(kind.get()) != SQLITE_DONE) {
        fail("identity_mismatch", "Snapshot has no ordinary identity table.");
    }
    auto stmt = prepare(
        raw, "SELECT singleton,role,instance_id,owner_id,schema_version FROM database_identity");
    if (sqlite3_step(stmt.get()) != SQLITE_ROW || sqlite3_column_int(stmt.get(), 0) != 1 ||
        text(stmt.get(), 1) != expected.role || text(stmt.get(), 2) != expected.instance ||
        text(stmt.get(), 3) != expected.owner || sqlite3_column_int(stmt.get(), 4) != version ||
        sqlite3_step(stmt.get()) != SQLITE_DONE) {
        fail("identity_mismatch", "Snapshot does not match the independently supplied identity.");
    }
    check(sqlite3_set_authorizer(raw, authorize, nullptr), raw);
}
std::string Snapshot::query_impl(std::string_view sql, QueryLimits limits) {
    limits.rows = std::min(limits.rows, std::size_t{10000});
    limits.output_bytes = std::min(limits.output_bytes, 16 * mib);
    limits.timeout =
        std::clamp(limits.timeout, std::chrono::milliseconds{0}, std::chrono::milliseconds{5000});
    if (sql.empty() || sql.size() > 64 * 1024 || sql.find('\0') != std::string_view::npos) {
        fail("query_refused", "SQL must be nonempty, NUL-free, and at most 64 KiB.");
    }
    auto deadline = Clock::now() + limits.timeout;
    sqlite3_progress_handler(
        db_.get(), 1000,
        [](void* value) {
            return Clock::now() >= *static_cast<const Clock::time_point*>(value) ? 1 : 0;
        },
        &deadline);
    struct Reset {
        sqlite3* db;
        ~Reset() {
            sqlite3_progress_handler(db, 0, nullptr, nullptr);
        }
    } reset{db_.get()};
    auto budget = [&] {
        if (Clock::now() >= deadline) {
            fail("query_timeout", "Query exceeded its execution deadline.");
        }
    };
    sqlite3_stmt* raw = nullptr;
    const char* tail = nullptr;
    const std::string source(sql);
    const int rc = sqlite3_prepare_v3(db_.get(), source.c_str(), static_cast<int>(source.size()),
                                      SQLITE_PREPARE_NO_VTAB, &raw, &tail);
    Statement stmt(raw, sqlite3_finalize);
    check(rc, db_.get());
    if (!raw || !sqlite3_stmt_readonly(raw) || sqlite3_stmt_isexplain(raw) ||
        sqlite3_bind_parameter_count(raw) != 0 ||
        !std::all_of(tail, source.c_str() + source.size(), whitespace)) {
        fail("query_refused",
             "Supply exactly one SELECT with no parameters or non-whitespace tail.");
    }
    std::string out;
    auto append = [&](std::string_view value) {
        budget();
        if (value.size() > limits.output_bytes - out.size()) {
            fail("query_limit", "Query output exceeds its byte limit.");
        }
        out += value;
    };
    append("{\"columns\":[");
    const int columns = sqlite3_column_count(raw);
    for (int c = 0; c < columns; ++c) {
        if (c) {
            append(",");
        }
        append(quote(sqlite3_column_name(raw, c), limits.output_bytes - out.size()));
    }
    append("],\"rows\":[");
    std::size_t rows = 0;
    for (;;) {
        budget();
        const int step = sqlite3_step(raw);
        if (step == SQLITE_DONE) {
            break;
        }
        check(step, db_.get());
        if (rows == limits.rows) {
            fail("query_limit", "Query exceeds its row limit.");
        }
        if (rows++) {
            append(",");
        }
        append("[");
        for (int c = 0; c < columns; ++c) {
            if (c) {
                append(",");
            }
            append(cell(raw, c, limits.output_bytes - out.size()));
        }
        append("]");
    }
    append("],\"truncated\":false}");
    return out;
}
} // namespace aslice::db
