#!/bin/sh
# Reuse a provisioned development image; all writes stay in the disposable container.
set -eu
mode=${1:-OFF}
case "$mode" in
    OFF) standard_library=libc++ ;;
    ON) standard_library=libstdc++ ;;
    *) echo 'Expected sanitizer mode OFF or ON.' >&2; exit 2 ;;
esac
cmake -S /src -B /build -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
    -DASLICE_SANITIZERS="$mode" -DCMAKE_CXX_FLAGS="-stdlib=$standard_library"
cmake --build /build -j 4
cmake --build /build --target format-check tidy
ctest --test-dir /build --output-on-failure -j 2
