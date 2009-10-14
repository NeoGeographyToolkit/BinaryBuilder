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
    echo ${__OS:="$(uname -s)"}
}

shared_name() {
    case $(getOS) in
        Linux)  echo "so";;
        Darwin) echo "dylib";;
        *) die "Unknown OS: $(getOS)"
    esac
}

die() {
    echo "$1" >&2
    kill -s SIGTERM $self
}

set_rpath_linux() {
    local file="$1"
    shift 1
    local rpath i
    for i in "$@"; do
        rpath="${rpath}${rpath:+:}\$ORIGIN/$i"
    done

    chrpath -r "$rpath" "$file" || die "chrpath failed"
}


set_rpath_darwin() {
    local file="$1"
    shift 1
    otool -L $file | awk 'NR > 2 {print $1}' | while read entry; do

        if is_whitelist $entry; then
            continue
        fi

        local origin="$(dirname $file)"
        local base="$(basename $entry)"
        local new=""

        for rpath in "$@"; do
            if [[ -r "$origin/$rpath/$base" ]]; then
                new="@executable_path/$rpath/$base"
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
        Linux)  set_rpath_linux $* ;;
        Darwin) set_rpath_darwin $* ;;
        *) die "Unknown OS: $(getOS)"
    esac
}
