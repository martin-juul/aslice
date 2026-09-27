#!/bin/sh
# Run inside the development image, or pass the executable and repository root.
set -eu
aslice=${1:-/build/aslice}
repo=${2:-/src}
work=$(mktemp -d)
trap 'chmod -R u+w "$work"; rm -rf "$work"' EXIT
prefix="$work/prefix"
catalog="$repo/tests/fixtures/prototype/catalog-v1.json"
run() { command="$1"; shift; "$aslice" dev fixture "$command" --prefix "$prefix" --catalog "$catalog" "$@"; }
run init
run plan hello
first=$(run install hello | python3 -c 'import json,sys; print(json.load(sys.stdin)["generation"])')
printf '\nInstalled program:\n'
"$prefix/profiles/default/bin/hello"
run list
catalog="$repo/tests/fixtures/prototype/catalog-v2.json"
run upgrade
printf '\nUpgraded program:\n'
"$prefix/profiles/default/bin/hello"
run rollback "$first"
printf '\nRolled-back program:\n'
"$prefix/profiles/default/bin/hello"
run verify
run uninstall hello
run autoremove
run list
