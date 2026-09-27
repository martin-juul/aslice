/* SPDX-License-Identifier: Apache-2.0
 * Reproduce the null-environment launch used by the unmodified LLDB binary.
 */
#include <stdio.h>
#include <unistd.h>

int main(void) {
    char* const arguments[] = {"/bin/echo", "empty-environment", NULL};
    execve(arguments[0], arguments, NULL);
    perror("execve with an empty environment");
    return 1;
}
