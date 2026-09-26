#include "cli/registry.hpp"
#ifdef __MINGW32__
#include <corecrt.h>
// Preserve literal constraints instead of expanding local filenames.
int _CRT_glob = 0;
#endif
int main(int argc, char** argv) {
    return aslice::cli::dispatch(argc, argv);
}
