cmake_minimum_required(VERSION 3.20)
project(aslice VERSION 0.0.1 LANGUAGES C CXX)

# The Windows bootstrap installs libraries for CLion's bundled MinGW here.
# Keep the real headers and link targets available to native IDE builds.
if(MINGW)
  list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/build/windows-deps/x64-mingw-static")
  set(OPENSSL_USE_STATIC_LIBS TRUE)
endif()

function(aslice_bundle_runtime target)
  if(MINGW)
    get_filename_component(compiler_directory "${CMAKE_CXX_COMPILER}" DIRECTORY)
    foreach(runtime libstdc++-6.dll libgcc_s_seh-1.dll libwinpthread-1.dll)
      if(NOT EXISTS "${compiler_directory}/${runtime}")
        message(FATAL_ERROR "Missing MinGW runtime: ${compiler_directory}/${runtime}")
      endif()
      add_custom_command(TARGET ${target} POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${compiler_directory}/${runtime}" "$<TARGET_FILE_DIR:${target}>/${runtime}"
        VERBATIM)
    endforeach()
  endif()
endfunction()

# This build exercises portable code. It is not the release toolchain.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(FetchContent)
if(POLICY CMP0135)
  cmake_policy(SET CMP0135 NEW)
endif()
FetchContent_Declare(sqlite
  URL https://sqlite.org/2026/sqlite-amalgamation-3510300.zip
  URL_HASH SHA256=acb1e6f5d832484bf6d32b681e858c38add8b2acdfd42ac5df24b8afb46552b4
  TLS_VERIFY TRUE
  TIMEOUT 120
)
FetchContent_MakeAvailable(sqlite)
# Cross-check against SQLite's published release checksum, not just our ZIP pin.
file(SHA3_256 "${sqlite_SOURCE_DIR}/sqlite3.c" sqlite_source_hash)
if(NOT sqlite_source_hash STREQUAL "32d5424f97e0a7fc5ed2f6335afbb58be4e0298bd7117a34e39d345ff13d859e")
  message(FATAL_ERROR "SQLite source does not match the reviewed 3.51.3 release")
endif()
add_library(aslice_sqlite STATIC "${sqlite_SOURCE_DIR}/sqlite3.c")
target_include_directories(aslice_sqlite PUBLIC "${sqlite_SOURCE_DIR}")
target_compile_definitions(aslice_sqlite PRIVATE SQLITE_THREADSAFE=1
  SQLITE_OMIT_LOAD_EXTENSION SQLITE_DQS=0 SQLITE_DEFAULT_MEMSTATUS=1
  SQLITE_MAX_MMAP_SIZE=0 SQLITE_TEMP_STORE=3 SQLITE_TRUSTED_SCHEMA=0)
find_package(Threads REQUIRED)
target_link_libraries(aslice_sqlite PUBLIC Threads::Threads)
if(UNIX)
  target_link_libraries(aslice_sqlite PUBLIC m)
endif()
add_library(aslice_db STATIC src/db/query.cpp)
target_include_directories(aslice_db PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_link_libraries(aslice_db PUBLIC aslice_sqlite)

set(schema_header "${CMAKE_CURRENT_BINARY_DIR}/generated/schemas.hpp")
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(WRITE "${schema_header}" "#pragma once\n#include <array>\n#include <string_view>\nnamespace aslice {\nstruct Schema { std::string_view role; std::string_view sql; };\ninline constexpr std::array<Schema, 6> schemas{{\n")
foreach(role client-state client-cache system-state coordinator publisher release-signer)
  set(source "${CMAKE_CURRENT_SOURCE_DIR}/docs/sqlite/${role}.sql")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${source}")
  file(READ "${source}" ddl)
  string(FIND "${ddl}" ")aslice_sql\"" delimiter_position)
  if(NOT delimiter_position EQUAL -1)
    message(FATAL_ERROR "SQL contains the embedding delimiter: ${source}")
  endif()
  file(APPEND "${schema_header}" "{\"${role}\", R\"aslice_sql(${ddl})aslice_sql\"},\n")
endforeach()
file(APPEND "${schema_header}" "}};\n}\n")

find_package(nlohmann_json 3.11 CONFIG QUIET)
if(NOT nlohmann_json_FOUND)
  set(JSON_BuildTests OFF CACHE BOOL "Build JSON dependency tests" FORCE)
  set(JSON_Install OFF CACHE BOOL "Install JSON dependency" FORCE)
  FetchContent_Declare(nlohmann_json
    URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
    URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
    TLS_VERIFY TRUE
    TIMEOUT 120)
  FetchContent_MakeAvailable(nlohmann_json)
endif()
find_package(OpenSSL REQUIRED COMPONENTS Crypto)
find_package(zstd CONFIG REQUIRED)
if(TARGET zstd::libzstd_static)
  set(aslice_zstd_target zstd::libzstd_static)
else()
  set(aslice_zstd_target zstd::libzstd)
endif()

find_package(tl-expected 1.3.1 EXACT CONFIG QUIET)
if(NOT tl-expected_FOUND)
  set(EXPECTED_BUILD_TESTS OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(tl_expected
    URL https://github.com/TartanLlama/expected/archive/refs/tags/v1.3.1.tar.gz
    URL_HASH SHA512=764e11097fe6ff18499e0941288fbd1cac91fe68009e077ef803742d48dd38efa8cc57cd6207e7d384f577a11bcb9bff43d3d853ade20340af36fccaaa5d47ed
    TLS_VERIFY TRUE)
  FetchContent_MakeAvailable(tl_expected)
endif()
add_library(aslice_core STATIC src/core/support.cpp)
target_include_directories(aslice_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_link_libraries(aslice_core PUBLIC nlohmann_json::nlohmann_json tl::expected OpenSSL::Crypto)
target_link_libraries(aslice_db PUBLIC tl::expected)
add_library(aslice_package STATIC src/package/version.cpp src/package/candidate.cpp src/package/manifest.cpp src/package/slice.cpp)
target_link_libraries(aslice_package PUBLIC aslice_core ${aslice_zstd_target})
add_library(aslice_resolver STATIC src/resolver/solver.cpp)
target_link_libraries(aslice_resolver PUBLIC aslice_package)
add_library(aslice_fixture STATIC src/adapters/fixture.cpp)
target_link_libraries(aslice_fixture PUBLIC aslice_resolver)
add_library(aslice_platform STATIC)
if(WIN32)
  target_sources(aslice_platform PRIVATE src/platform/filesystem_windows.cpp)
else()
  target_sources(aslice_platform PRIVATE src/platform/filesystem_posix.cpp)
endif()
target_link_libraries(aslice_platform PUBLIC aslice_core)
add_library(aslice_store STATIC src/store/fixture_store.cpp)
target_link_libraries(aslice_store PUBLIC aslice_fixture aslice_platform)
add_library(aslice_profile STATIC src/profile/generation.cpp)
target_link_libraries(aslice_profile PUBLIC aslice_store)
add_executable(aslice src/cli/main.cpp src/cli/registry.cpp src/cli/fixture.cpp src/cli/inspect.cpp)
aslice_bundle_runtime(aslice)
target_link_libraries(aslice PRIVATE aslice_profile)
target_include_directories(aslice PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(aslice PRIVATE ASLICE_VERSION="${PROJECT_VERSION}-dev")
foreach(target aslice aslice_core aslice_package aslice_db aslice_resolver aslice_fixture aslice_platform aslice_store aslice_profile)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /WX)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
  endif()
endforeach()
option(ASLICE_SANITIZERS "Build owned C++ code with ASan and UBSan" OFF)
if(ASLICE_SANITIZERS)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
  foreach(target aslice aslice_core aslice_package aslice_db aslice_resolver aslice_fixture aslice_platform aslice_store aslice_profile)
    target_compile_options(${target} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(${target} PUBLIC -fsanitize=address,undefined)
  endforeach()
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_program(ASLICE_CLANG_FORMAT NAMES clang-format-20 clang-format)
find_program(ASLICE_CLANG_TIDY NAMES clang-tidy-20 clang-tidy)
foreach(mode format format-check tidy)
  add_custom_target(${mode}
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/quality.py"
      ${mode} --build "${CMAKE_CURRENT_BINARY_DIR}"
      --format-tool "${ASLICE_CLANG_FORMAT}" --tidy-tool "${ASLICE_CLANG_TIDY}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" VERBATIM)
endforeach()

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_executable(model_driver tests/model_driver.cpp)
  aslice_bundle_runtime(model_driver)
  target_link_libraries(model_driver PRIVATE aslice_fixture aslice_db)
  add_test(NAME models COMMAND model_driver "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/prototype/legacy-generation.json")
  add_test(NAME help COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_help.py" "$<TARGET_FILE:aslice>")
  add_test(NAME cli COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_cli.py" "$<TARGET_FILE:aslice>")
  add_test(NAME package COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_package.py" "$<TARGET_FILE:aslice>")
  add_test(NAME manifest COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_manifest.py" "$<TARGET_FILE:aslice>")
  add_executable(zstd_driver tests/zstd_driver.cpp)
  aslice_bundle_runtime(zstd_driver)
  target_link_libraries(zstd_driver PRIVATE ${aslice_zstd_target})
  add_test(NAME slice COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_slice.py" "$<TARGET_FILE:aslice>" "$<TARGET_FILE:zstd_driver>")
  set_tests_properties(slice PROPERTIES TIMEOUT 90)
  add_executable(query_driver tests/query_driver.cpp)
  aslice_bundle_runtime(query_driver)
  target_link_libraries(query_driver PRIVATE aslice_db)
  add_test(NAME query COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_query.py" "$<TARGET_FILE:query_driver>")
  set_tests_properties(query PROPERTIES TIMEOUT 45)
  foreach(target model_driver query_driver zstd_driver)
    if(MSVC)
      target_compile_options(${target} PRIVATE /W4 /WX)
    else()
      target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
  endforeach()
  if(UNIX)
    add_test(NAME lifecycle COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lifecycle.py" "$<TARGET_FILE:aslice>")
    set_tests_properties(lifecycle PROPERTIES TIMEOUT 60)
  endif()
endif()
