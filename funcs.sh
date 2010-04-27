#!/bin/bash

DARWIN_WHITELIST=(
/System/Library/Frameworks/AGL.framework/Versions/A/AGL
/System/Library/Frameworks/ApplicationServices.framework/Versions/A/ApplicationServices
/System/Library/Frameworks/Carbon.framework/Versions/A/Carbon
/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation
/System/Library/Frameworks/CoreServices.framework/Versions/A/CoreServices
/System/Library/Frameworks/GLUT.framework/Versions/A/GLUT
/System/Library/Frameworks/OpenGL.framework/Versions/A/OpenGL
/System/Library/Frameworks/vecLib.framework/Versions/A/vecLib
/System/Library/Frameworks/QuickTime.framework/Versions/A/QuickTime
/usr/lib/libSystem.B.dylib
/usr/lib/libgcc_s.1.dylib
/usr/lib/libstdc++.6.dylib
)

is_whitelist()
{
    local elem="$1"
    shift 1

    local i

    for i in "${DARWIN_WHITELIST[@]}"; do
        if [[ $i = $elem ]]; then
            return 0
        fi
    done
    return 1
}

getOS() {
    echo ${__OS:="$(uname -s | sed -e 's/Darwin/OSX/')"}
}

# Die from any subshell. Make sure you set $self before calling this.
die() {
    echo "$1" >&2
    kill -s SIGTERM $self
}

# Magic here:
# In linux, $ORIGIN means (to the dynamic loader)
# "Path to the thing currently being loaded" (so, either to the bin or to the lib)
# Therefore, construct an rpath made up of the origin, the path to the root of
# the dist, and then the given list of rpaths, which should be relative to the
# root of the dist.
set_rpath_linux() {
    local file="$1"
    local root="$2"
    shift 2
    local rpath elt
    for elt in "$@"; do
        rpath="${rpath}${rpath:+:}\$ORIGIN/${root}${elt}"
    done

    chrpath -r "$rpath" "$file" || die "chrpath failed"
}


# Magic here:
# much like Linux's $ORIGIN, @executable_path is a runtime-determined value...
# except that it always points to the BINARY that caused the load, not the
# library (if it is one)
set_rpath_darwin() {
    local file="$1"
    local root="$2"
    shift 2
    # Skip the first line of otool, which is the object's SELF entry
    otool -L $file | awk 'NR > 1 {print $1}' | while read entry; do

        # Don't warn me about things I know I'm skipping
        if is_whitelist $entry; then
            continue
        fi

        local base="$(basename $entry)"
        local new=""

        # OSX rpath points to one specific file, not anything that matches the
        # library SONAME. Therefore, do the library discovery right now, rather
        # than delaying until runtime like in Linux

        for rpath in "$@"; do
            if [[ -r "${file}/${root}/$rpath/$base" ]]; then
                # This code assumes that the binaries are installed at $DISTDIR/bin
                new="@executable_path/../$rpath/$base"
            fi
        done
        if [[ -n $new ]]; then
            install_name_tool -change $entry $new $file || die "FAILED: install_name_tool -change $entry $new $file"
        else
            echo "Skipped $file: $entry"
        fi
    done
}

set_rpath() {
    case $(getOS) in
        Linux) set_rpath_linux $* ;;
        OSX)   set_rpath_darwin $* ;;
        *) die "Unknown OS: $(getOS)"
    esac
}

get_relative_path() {
    local root="$1"
    local path="$2"

    root="$(cd $root && pwd)"
    path="$(cd $(dirname $path) && pwd)"

    if [[ -z $root ]] || [[ -z $path ]]; then
        echo "root and path must exist" >&2
        return 1
    fi


    # if $root isprefixof $path
    if [[ ${path##$root} == $path ]]; then
        echo "Path is not inside root" >&2
        return 1
    fi

    local ret

    while [[ $path != / ]]; do
        if [[ $path == $root ]]; then
            break
        fi
        path="$(dirname $path)"
        ret="../$ret"
    done
    echo $ret
}
