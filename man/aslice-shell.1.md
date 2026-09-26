% ASLICE-SHELL(1) aslice v0.1
% aslice contributors
% September 2026

# NAME

aslice-shell — print shell integration, configure aslice, and read help

# SYNOPSIS

`aslice shellenv`

`aslice init` *shell*

`aslice config get` *key*

`aslice config set` *key* *value*

`aslice help` *command*

# DESCRIPTION

These are specified interfaces; this page does not establish completed implementation.

**shellenv** prints PATH, MANPATH, INFOPATH, and private trust-store exports for the
current profile. It is pure output and writes no files. **init** prints the shell
integration for bash, zsh, or fish; the shell function evaluates the exports from
`aslice use`. A child process cannot change its parent's environment: evaluate the
output in that shell to apply it. Use shell-appropriate syntax; the example is zsh.

**config get** reads a configuration key; **config set** writes the key's value in
`<prefix>/etc/aslice.toml` (`~/.aslice/etc/aslice.toml` for per-user installs).
The existing overview specifies get/set, but does not fully define get's
missing-key result or complex-value CLI encoding. Do not infer a list/reset verb.
The [MANUAL configuration reference](../docs/MANUAL.md#configuration-reference)
defines supported keys and defaults. For example, `flavor` is a CPU ceiling,
not permission to execute unsupported instructions. `db.lock_timeout` alone does
not authorize waiting; use the global `--wait` option when waiting is intended.

**help** prints the command's man-page text. Related commands share a family page;
the family map in [man/README](README.md#command-families) identifies the owner.
Help rendering and installed alias generation remain implementation work.

# ENVIRONMENT AND LIMITS

`ASLICE_USE_<RUNTIME>` supplies session selection. `SSL_CERT_FILE`,
`CURL_CA_BUNDLE`, and `GIT_SSL_CAINFO` point compatible userland clients at the
aslice CA bundle. These exports do not replace the OS TLS implementation.
Environment overrides are visible through doctor's environment checks.
Neither shell command edits shell startup files by itself.

# EXAMPLES

```sh
aslice shellenv
eval "$(aslice init zsh)"
aslice config get flavor
aslice config set flavor v2
aslice help install
```

# EXIT STATUS

The common statuses in [aslice(1)](aslice.1.md#exit-status) apply where
relevant: 0 success, 1 error or recovery required, 2 plan refused, 4 contention
without unresolved recovery, and 130 safely completed cancellation. No additional
family-specific numeric statuses are specified.

# SEE ALSO

[aslice(1)](aslice.1.md), [aslice-use(1)](aslice-use.1.md), [aslice-doctor(1)](aslice-doctor.1.md),
[MANUAL](../docs/MANUAL.md#configuration-reference),
[DESIGN](../docs/DESIGN.md#multi-version-runtimes-use-pin-default--and-version-bound-extensions)
