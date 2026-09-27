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
add_library(aslice_core STATIC src/core/support.cpp src/core/lock_wait.cpp)
target_include_directories(aslice_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_link_libraries(aslice_core PUBLIC nlohmann_json::nlohmann_json tl::expected OpenSSL::Crypto)
add_library(aslice_helper STATIC src/helper/protocol.cpp)
target_link_libraries(aslice_helper PUBLIC aslice_core Threads::Threads)
target_link_libraries(aslice_db PUBLIC tl::expected)
add_library(aslice_package STATIC src/package/version.cpp src/package/candidate.cpp src/package/manifest.cpp src/package/slice.cpp)
target_link_libraries(aslice_package PUBLIC aslice_core ${aslice_zstd_target})
add_library(aslice_resolver STATIC src/resolver/solver.cpp)
target_link_libraries(aslice_resolver PUBLIC aslice_package)
add_library(aslice_fixture STATIC src/adapters/fixture.cpp)
target_link_libraries(aslice_fixture PUBLIC aslice_resolver)
add_library(aslice_platform STATIC src/platform/target_filesystem.cpp src/platform/target_filesystem_native.cpp src/platform/wait_clock.cpp)
if(WIN32)
  target_sources(aslice_platform PRIVATE src/platform/filesystem_windows.cpp)
else()
  target_sources(aslice_platform PRIVATE src/platform/filesystem_posix.cpp)
endif()
target_link_libraries(aslice_platform PUBLIC aslice_core)
target_link_libraries(aslice_platform PUBLIC Threads::Threads)
target_link_libraries(aslice_package PUBLIC aslice_platform)
add_library(aslice_helper_inspection STATIC src/helper/inspection.cpp)
target_link_libraries(aslice_helper_inspection PUBLIC aslice_helper aslice_package)
add_library(aslice_helper_process STATIC src/platform/helper_process.cpp)
target_link_libraries(aslice_helper_process PUBLIC aslice_helper_inspection)
if(WIN32)
  target_link_libraries(aslice_helper_process PRIVATE advapi32)
endif()
add_library(aslice_store STATIC src/store/fixture_store.cpp)
target_link_libraries(aslice_store PUBLIC aslice_fixture aslice_platform)
add_library(aslice_profile STATIC src/profile/generation.cpp)
target_link_libraries(aslice_profile PUBLIC aslice_store)
add_library(aslice_cli STATIC src/cli/registry.cpp src/cli/fixture.cpp src/cli/inspect.cpp)
target_link_libraries(aslice_cli PUBLIC aslice_profile)
target_include_directories(aslice_cli PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(aslice_cli PRIVATE ASLICE_VERSION="${PROJECT_VERSION}-dev")
add_executable(aslice src/cli/main.cpp)
aslice_bundle_runtime(aslice)
target_link_libraries(aslice PRIVATE aslice_cli aslice_helper_process)
target_include_directories(aslice PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_compile_definitions(aslice PRIVATE ASLICE_VERSION="${PROJECT_VERSION}-dev")
add_library(aslice_simulator STATIC src/platform/simulator.cpp src/platform/target_filesystem_simulator.cpp src/platform/wait_clock_simulator.cpp)
target_link_libraries(aslice_simulator PUBLIC aslice_platform)
if(WIN32)
  target_link_libraries(aslice_simulator PRIVATE ws2_32)
endif()
add_executable(aslice-simulator src/cli/simulator_main.cpp)
target_link_libraries(aslice-simulator PRIVATE aslice_cli aslice_simulator)
aslice_bundle_runtime(aslice-simulator)
foreach(target aslice aslice_cli aslice-simulator aslice_simulator aslice_core aslice_helper aslice_helper_inspection aslice_helper_process aslice_package aslice_db aslice_resolver aslice_fixture aslice_platform aslice_store aslice_profile)
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
  foreach(target aslice aslice_cli aslice-simulator aslice_simulator aslice_core aslice_helper aslice_helper_inspection aslice_helper_process aslice_package aslice_db aslice_resolver aslice_fixture aslice_platform aslice_store aslice_profile)
    target_compile_options(${target} PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(${target} PUBLIC -fsanitize=address,undefined)
  endforeach()
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_program(ASLICE_CLANG_FORMAT NAMES clang-format-22 clang-format)
find_program(ASLICE_CLANG_TIDY NAMES clang-tidy-22 clang-tidy)
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
  add_test(NAME requirements COMMAND "${Python3_EXECUTABLE}" -m unittest discover
    -s "${CMAKE_CURRENT_SOURCE_DIR}/tests" -p test_requirements.py)
  set_tests_properties(requirements PROPERTIES TIMEOUT 45)
  add_test(NAME requirement-inventory COMMAND "${Python3_EXECUTABLE}" -m tools.simulator
    coverage --gate development --output "${CMAKE_CURRENT_BINARY_DIR}/requirement-coverage.json")
  set_tests_properties(requirement-inventory PROPERTIES
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" TIMEOUT 45)
  add_executable(lock_wait_tests tests/lock_wait_tests.cpp)
  target_link_libraries(lock_wait_tests PRIVATE aslice_platform)
  aslice_bundle_runtime(lock_wait_tests)
  add_test(NAME lock-wait COMMAND lock_wait_tests)
  set_tests_properties(lock-wait PROPERTIES TIMEOUT 30)
  add_executable(helper_protocol_tests tests/helper_protocol_tests.cpp)
  target_link_libraries(helper_protocol_tests PRIVATE aslice_helper aslice_package)
  aslice_bundle_runtime(helper_protocol_tests)
  add_test(NAME helper-protocol COMMAND helper_protocol_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/artifact-manifest.json")
  set_tests_properties(helper-protocol PROPERTIES TIMEOUT 30)
  add_executable(helper_process_tests tests/helper_process_tests.cpp)
  target_link_libraries(helper_process_tests PRIVATE aslice_helper_process)
  aslice_bundle_runtime(helper_process_tests)
  add_test(NAME helper-process COMMAND helper_process_tests "$<TARGET_FILE:aslice>"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/artifact-manifest.json")
  set_tests_properties(helper-process PROPERTIES TIMEOUT 60 SKIP_RETURN_CODE 77)
  add_test(NAME helper-channel COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_helper_process.py" "$<TARGET_FILE:aslice>")
  set_tests_properties(helper-channel PROPERTIES TIMEOUT 45)
  add_executable(simulator_helper_driver tests/simulator_helper_driver.cpp)
  target_link_libraries(simulator_helper_driver PRIVATE aslice_helper_inspection aslice_simulator)
  aslice_bundle_runtime(simulator_helper_driver)
  add_test(NAME simulator-helper COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_helper_channels.py"
    "$<TARGET_FILE:simulator_helper_driver>" "$<TARGET_FILE:aslice>")
  set_tests_properties(simulator-helper PROPERTIES TIMEOUT 90)
  add_test(NAME simulator-helper-replay COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_helper_replay.py"
    "$<TARGET_FILE:simulator_helper_driver>" "$<TARGET_FILE:aslice-simulator>")
  set_tests_properties(simulator-helper-replay PROPERTIES TIMEOUT 120)
  add_executable(lock_wait_driver tests/lock_wait_driver.cpp)
  target_link_libraries(lock_wait_driver PRIVATE aslice_simulator)
  aslice_bundle_runtime(lock_wait_driver)
  add_test(NAME simulator-lock-wait COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_lock_wait.py" "$<TARGET_FILE:lock_wait_driver>")
  set_tests_properties(simulator-lock-wait PROPERTIES TIMEOUT 60)
  add_executable(platform_read_driver tests/platform_read_driver.cpp)
  target_link_libraries(platform_read_driver PRIVATE aslice_platform)
  aslice_bundle_runtime(platform_read_driver)
  add_test(NAME platform-read COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_platform_read.py" "$<TARGET_FILE:platform_read_driver>")
  set_tests_properties(platform-read PROPERTIES TIMEOUT 45)
  add_executable(simulator_driver tests/simulator_driver.cpp)
  target_link_libraries(simulator_driver PRIVATE aslice_simulator)
  aslice_bundle_runtime(simulator_driver)
  add_test(NAME simulator COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_simulator.py"
    "$<TARGET_FILE:aslice-simulator>" "$<TARGET_FILE:simulator_driver>" "$<TARGET_FILE:aslice>")
  set_tests_properties(simulator PROPERTIES TIMEOUT 180)
  add_test(NAME simulator-process COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_process_lifetime.py")
  set_tests_properties(simulator-process PROPERTIES TIMEOUT 60)
  add_test(NAME simulator-credentials COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_credentials.py"
    "$<TARGET_FILE:simulator_driver>" "$<TARGET_FILE:aslice-simulator>")
  set_tests_properties(simulator-credentials PROPERTIES TIMEOUT 90)
  add_test(NAME simulator-lifecycle COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_fixture_lifecycle.py"
    "$<TARGET_FILE:aslice-simulator>")
  set_tests_properties(simulator-lifecycle PROPERTIES TIMEOUT 300)
  add_test(NAME simulator-inspection COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/simulator/test_inspection.py"
    "$<TARGET_FILE:aslice-simulator>")
  set_tests_properties(simulator-inspection PROPERTIES TIMEOUT 180)
  add_executable(model_driver tests/model_driver.cpp)
  aslice_bundle_runtime(model_driver)
  target_link_libraries(model_driver PRIVATE aslice_fixture aslice_db)
  add_test(NAME models COMMAND model_driver "${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/prototype/legacy-generation.json")
  add_test(NAME help COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_help.py" "$<TARGET_FILE:aslice>")
  add_test(NAME cli COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_cli.py" "$<TARGET_FILE:aslice>")
  add_test(NAME package COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_package.py" "$<TARGET_FILE:aslice>")
  add_test(NAME solver-oracle COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_solver_oracle.py" "$<TARGET_FILE:aslice>")
  set_tests_properties(solver-oracle PROPERTIES TIMEOUT 60)
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
  foreach(target model_driver query_driver zstd_driver simulator_driver simulator_helper_driver platform_read_driver lock_wait_tests lock_wait_driver helper_protocol_tests helper_process_tests)
    if(MSVC)
      target_compile_options(${target} PRIVATE /W4 /WX)
    else()
      target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
  endforeach()
  if(UNIX)
    add_executable(platform_directory_driver tests/platform_directory_driver.cpp)
    target_link_libraries(platform_directory_driver PRIVATE aslice_platform)
    target_compile_options(platform_directory_driver PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME platform-directory COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_platform_directory.py" "$<TARGET_FILE:platform_directory_driver>")
    set_tests_properties(platform-directory PROPERTIES TIMEOUT 30)
    add_test(NAME lifecycle COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_lifecycle.py" "$<TARGET_FILE:aslice>")
    set_tests_properties(lifecycle PROPERTIES TIMEOUT 60)
  endif()
endif()
