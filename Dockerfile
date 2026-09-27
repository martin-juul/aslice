FROM ubuntu:26.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates clang-22 clang-format-22 clang-tidy-22 libclang-rt-22-dev libc++-22-dev libc++abi-22-dev cmake ninja-build python3 \
    nlohmann-json3-dev libssl-dev libzstd-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
ARG ASLICE_SANITIZERS=OFF
# Ubuntu's libc++abi exception-message deallocation triggers ASan's mismatch check
# (llvm/llvm-project#59432). Keep libc++ coverage in the ordinary build and run
# the sanitizer matrix with libstdc++; no sanitizer diagnostics are disabled.
RUN if [ "$ASLICE_SANITIZERS" = ON ]; then standard_library=libstdc++; else standard_library=libc++; fi \
    && cmake -S . -B /build -G Ninja \
    -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=clang-22 -DCMAKE_CXX_COMPILER=clang++-22 \
    -DASLICE_SANITIZERS=${ASLICE_SANITIZERS} \
    -DCMAKE_CXX_FLAGS=-stdlib=$standard_library \
    && cmake --build /build \
    && cmake --build /build --target format-check tidy \
    && ctest --test-dir /build --output-on-failure
ENTRYPOINT ["/build/aslice"]
CMD ["--help"]
