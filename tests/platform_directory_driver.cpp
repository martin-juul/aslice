// Exercise actual native directory operations; no simulated filesystem here.
#include "core/support.hpp"
#include "platform/paths.hpp"
#include "platform/target_filesystem.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        return 2;
    }
    try {
        aslice::platform::NativeFileSystem filesystem;
        const auto root = filesystem.absolute(argv[1]);
        const auto real = root / "real";
        const auto alias = root / "alias";
        filesystem.mkdir(real);
        filesystem.permissions(real, 0700);
        filesystem.write_new(real / "file", "original", 0600);
        filesystem.write_new(real / ".lock", "", 0600);
        filesystem.create_symlink("real", alias);
        auto refuses = [](auto action) {
            bool refused = false;
            try {
                action();
            } catch (const aslice::core::Error&) {
                refused = true;
            }
            aslice::core::require(refused, "operation followed a symlinked ancestor");
        };
        refuses([&] {
            filesystem.list(alias);
        });
        refuses([&] {
            filesystem.status(alias / "file");
        });
        refuses([&] {
            filesystem.read(alias / "file", 100);
        });
        refuses([&] {
            filesystem.write_new(alias / "created", "unsafe");
        });
        refuses([&] {
            filesystem.mkdir(alias / "child");
        });
        refuses([&] {
            filesystem.permissions(alias / "file", 0777);
        });
        refuses([&] {
            filesystem.create_symlink("file", alias / "link");
        });
        refuses([&] {
            filesystem.rename(alias / "file", root / "stolen");
        });
        refuses([&] {
            filesystem.rename(real / "file", alias / "moved");
        });
        refuses([&] {
            filesystem.remove(alias / "file");
        });
        refuses([&] {
            filesystem.sync_directory(alias);
        });
        refuses([&] {
            filesystem.lock(alias);
        });
        refuses([&] {
            filesystem.check_private_directory(alias);
        });
        aslice::core::require(filesystem.read(real / "file", 100) == "original" &&
                                  filesystem.status(real / "file").mode == 0600 &&
                                  filesystem.list(real).size() == 2,
                              "refused operation changed the original directory");
        aslice::core::require(filesystem.read_symlink(alias) == "real", "wrong link target");
        filesystem.remove(alias); // Removing the link itself is permitted.
        filesystem.rename(real / "file", real / "renamed");
        filesystem.sync_directory(real);
        filesystem.remove(real / "renamed");
        filesystem.remove(real / ".lock");
        filesystem.remove(real);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
