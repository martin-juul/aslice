// Test-only adapter: fixture files and supplied identities are not authorization.
#include "db/query.hpp"
#include <exception>
#include <fstream>
#include <iostream>
#include <iterator>
#include <span>
#include <sqlite3.h>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>
#ifdef _WIN32
#include <cstdio>
#include <fcntl.h>
#include <io.h>
#include <stdio.h>
#endif

int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--sqlite-version") {
        std::cout << sqlite3_libversion() << '\n' << sqlite3_sourceid() << '\n';
        return 0;
    }
    if (argc != 9) {
        return 2;
    }
    try {
        std::ifstream input(argv[1], std::ios::binary);
        if (!input) {
            throw std::runtime_error("Cannot open test snapshot.");
        }
        std::vector<char> bytes{std::istreambuf_iterator<char>(input), {}};
        auto snapshot = aslice::db::Snapshot::create(std::as_bytes(std::span(bytes)),
                                                     {argv[2], argv[3], argv[4]});
        if (!snapshot) {
            std::cerr << snapshot.error().code << ": " << snapshot.error().message << '\n';
            return 2;
        }
        aslice::db::QueryLimits limits{std::stoull(argv[6]), std::stoull(argv[7]),
                                       std::chrono::milliseconds{std::stoll(argv[8])}};
        std::string sql = argv[5];
        if (sql == "--stdin-sql") {
#ifdef _WIN32
            _setmode(_fileno(stdin), _O_BINARY);
#endif
            sql.assign(std::istreambuf_iterator<char>(std::cin), {});
        }
        const auto result = snapshot->query(sql, limits);
        if (!result) {
            std::cerr << result.error().code << ": " << result.error().message << '\n';
            return 2;
        }
        std::cout << *result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
