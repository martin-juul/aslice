// Test fixture codec; archive acceptance is always exercised through aslice.
#include <cstddef>
#include <iostream>
#include <iterator>
#include <string>
#include <string_view>
#include <zstd.h>
#ifdef _WIN32
#include <cstdio>
#include <fcntl.h>
#include <io.h>
#include <stdio.h>
#endif
int main(int argc, char** argv) {
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    if (argc != 2) {
        return 2;
    }
    const std::string input{std::istreambuf_iterator<char>(std::cin), {}};
    if (input.size() > 128 * 1024 * 1024) {
        return 2;
    }
    const bool compress = std::string_view(argv[1]) == "compress";
    const auto capacity = compress ? ZSTD_compressBound(input.size())
                                   : ZSTD_getFrameContentSize(input.data(), input.size());
    if (capacity > 128 * 1024 * 1024) {
        return 2;
    }
    std::string output(static_cast<std::size_t>(capacity), '\0');
    const auto size =
        compress ? ZSTD_compress(output.data(), output.size(), input.data(), input.size(), 3)
                 : ZSTD_decompress(output.data(), output.size(), input.data(), input.size());
    if (ZSTD_isError(size)) {
        return 1;
    }
    std::cout.write(output.data(), static_cast<std::streamsize>(size));
    return std::cout.good() ? 0 : 1;
}
