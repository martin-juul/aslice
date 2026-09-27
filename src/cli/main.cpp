#include "cli/registry.hpp"
#include "platform/helper_process.hpp"
#include "platform/target_filesystem.hpp"
#ifdef __MINGW32__
#include <_mingw.h>
// Preserve literal constraints instead of expanding local filenames.
int _CRT_glob = 0;
#endif
int main(int argc, char** argv) {
    if (const auto status = aslice::platform::inspection_helper_entry(argc, argv)) {
        return *status;
    }
    aslice::platform::NativeFileSystem filesystem;
    return aslice::cli::dispatch(argc, argv, filesystem);
}
