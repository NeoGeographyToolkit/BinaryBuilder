#!/bin/sh
if test -z "$ISISROOT"; then
    echo "Please set ISISROOT before you run $0" >&2
    exit 1
fi

TOPLEVEL="$(cd $(dirname $0)/.. && pwd)"
LIB="${TOPLEVEL}/lib"
PROGRAM="${TOPLEVEL}/libexec/$(basename $0)"

case $(uname -s) in
    Linux)
        export LD_LIBRARY_PATH="$ISISROOT/lib:$ISISROOT/3rdParty/lib:${LIB}${LD_LIBRARY_PATH:+:}$LD_LIBRARY_PATH"
        export OSG_LIBRARY_PATH="${LD_LIBRARY_PATH}"
        ;;
    Darwin)
        export DYLD_FALLBACK_LIBRARY_PATH="$ISISROOT/lib:$ISISROOT/3rdParty/lib:${LIB}${DYLD_FALLBACK_LIBRARY_PATH:+:}$DYLD_FALLBACK_LIBRARY_PATH"
        export DYLD_FALLBACK_FRAMEWORK_PATH="$ISISROOT/lib:$ISISROOT/3rdParty/lib:${LIB}${DYLD_FALLBACK_FRAMEWORK_PATH:+:}$DYLD_FALLBACK_FRAMEWORK_PATH"
        export OSG_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH}"
        ;;
    *)
        echo "Unknown OS: $(uname -s)" >&2
        exit 1
        ;;
esac

if ! test -f "${PROGRAM}"; then
    echo "Could not find ${PROGRAM}" >&2
    echo "Is your stereo pipeline install incomplete?" >&2
    exit 1
fi
exec "${PROGRAM}" $*
