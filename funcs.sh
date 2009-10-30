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

die() {
    echo "$1" >&2
    kill -s SIGTERM $self
}

set_rpath_linux() {
    local file="$1"
    local bindir="$2"
    shift 2
    local rpath i root
    root=$(cd $bindir/.. && pwd)
    for i in "$@"; do
        local relpath=$(get_relative_path $root $file)
        rpath="${rpath}${rpath:+:}\$ORIGIN/${relpath}$i"
    done

    chrpath -r "$rpath" "$file" || die "chrpath failed"
}


set_rpath_darwin() {
    local file="$1"
    local bindir="$2"
    shift 2
    otool -L $file | awk 'NR > 1 {print $1}' | while read entry; do

        if is_whitelist $entry; then
            continue
        fi

        local base="$(basename $entry)"
        local new=""

        for rpath in "$@"; do
            if [[ -r "$bindir/../$rpath/$base" ]]; then
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
