/* SPDX-License-Identifier: Apache-2.0
 * Build on macOS, without simulator libraries or preload hooks.
 */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* Stable, visible breakpoint locations in both parent and spawned child. */
__attribute__((noinline)) int child_marker(int value) {
    return value + 1;
}

__attribute__((noinline)) int parent_marker(int value) {
    return value + 2;
}

int main(int argc, char** argv) {
    if (argc == 2 && strcmp(argv[1], "--child") == 0) {
        printf("child=%d\n", child_marker(40));
        return 0;
    }
    if (argc != 2) {
        fprintf(stderr, "usage: %s OUTPUT_DIRECTORY\n", argv[0]);
        return 2;
    }
    char temporary[4096], final[4096];
    if (snprintf(temporary, sizeof temporary, "%s/corpus.tmp", argv[1]) >= (int)sizeof temporary ||
        snprintf(final, sizeof final, "%s/corpus.txt", argv[1]) >= (int)sizeof final) {
        return 2;
    }
    int fd = open(temporary, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) {
        return 3;
    }
    const char text[] = "persistent corpus\n";
    if (write(fd, text, sizeof text - 1) != sizeof text - 1 || fsync(fd) != 0 || close(fd) != 0) {
        return 4;
    }
    if (rename(temporary, final) != 0) {
        return 5;
    }
    pid_t child = fork();
    if (child < 0) {
        return 6;
    }
    if (child == 0) {
        execl(argv[0], argv[0], "--child", (char*)0);
        _exit(7);
    }
    int status;
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        return 8;
    }
    printf("parent=%d\n", parent_marker(40));
    return 0;
}
