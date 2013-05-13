#!/bin/sh

self=$$
trap 'exit 1' TERM

TOPLEVEL="$(cd $(dirname $0)/.. && pwd)"
LIBEXEC="${ASP_DEBUG_DIR:-${TOPLEVEL}/libexec}"
ISISROOT=$TOPLEVEL

. "${LIBEXEC}/constants.sh"
. "${LIBEXEC}/libexec-funcs.sh"

check_isis
if [ "$(uname -s)" = "Linux" ]
then
    check_libc
fi
set_lib_paths "${TOPLEVEL}/lib"

PROGRAM="${LIBEXEC}/$(basename $0)"
if ! test -f "${PROGRAM}"; then
    msg "Could not find ${PROGRAM}"
    die "Is your Stereo Pipeline install incomplete?"
fi
exec "${PROGRAM}" "$@"
