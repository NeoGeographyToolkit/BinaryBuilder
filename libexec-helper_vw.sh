#!/bin/sh

self=$$
trap 'exit 1' TERM

TOPLEVEL="$(cd $(dirname $0)/.. && pwd)"
LIBEXEC="${ASP_DEBUG_DIR:-${TOPLEVEL}/libexec}"

. "${LIBEXEC}/constants.sh"
. "${LIBEXEC}/libexec-funcs.sh"

if [ "$(uname -s)" = "Linux" ]
then
    check_libc
fi

PROGRAM="${LIBEXEC}/$(basename $0)"

set_lib_paths "${TOPLEVEL}/lib"

if ! test -f "${PROGRAM}"; then
    msg "Could not find ${PROGRAM}"
    die "Is your Vision Workbench install incomplete?"
fi
exec "${PROGRAM}" "$@"
