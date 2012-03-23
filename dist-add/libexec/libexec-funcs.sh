#!/bin/sh

msg() {
    echo $* >&2
}

die() {
    msg $*
    kill $self
}

# Keep this in sync with the function in funcs.sh
isis_version() {
    local ROOT="${1:-$ISISROOT}"
    local ISIS_HEADER="${ROOT}/version"
    if test -s ${ISIS_HEADER}; then
        local version="$(head -1 < $ISIS_HEADER | sed 's/\([0-9]*\.[0-9]*\.[0-9]*\).*/\1/')"
    else
        local ISIS_HEADER="${ROOT}/src/base/objs/Constants/Constants.h"
        local version="$(grep version $ISIS_HEADER 2>/dev/null | cut -d\" -f2)"
    fi
    if test -z "${version}"; then
        msg "Unable to locate ISIS version header."
        msg "Expected it at $ISIS_HEADER"
        die "Perhaps your ISISROOT ($ROOT) is incorrect?"
    fi
    echo "$version"
}

check_isis() {
    if test -z "$ISISROOT"; then
        die "Please set ISISROOT before you run $0"
    fi
    local current="$(isis_version)"
    if test "$BAKED_ISIS_VERSION" != "$current"; then
        msg "This version of Stereo Pipeline requires version $BAKED_ISIS_VERSION"
        die "but your ISISROOT points to version $current"
    fi
}

set_lib_paths() {
    local add_paths="$ISISROOT/lib:$ISISROOT/3rdParty/lib:${1}"
    export GDAL_DATA=${TOPLEVEL}/share/gdal
    case $(uname -s) in
        Linux)
            export LD_LIBRARY_PATH="${add_paths}${LD_LIBRARY_PATH:+:}$LD_LIBRARY_PATH"
            export OSG_LIBRARY_PATH="${LD_LIBRARY_PATH}"
            ;;
        Darwin)
            export DYLD_FALLBACK_LIBRARY_PATH="${add_paths}${DYLD_FALLBACK_LIBRARY_PATH:+:}$DYLD_FALLBACK_LIBRARY_PATH"
            export DYLD_FALLBACK_FRAMEWORK_PATH="${add_paths}${DYLD_FALLBACK_FRAMEWORK_PATH:+:}$DYLD_FALLBACK_FRAMEWORK_PATH"
            export OSG_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH}"
            ;;
        *)
            die "Unknown OS: $(uname -s)"
            ;;
    esac
}
