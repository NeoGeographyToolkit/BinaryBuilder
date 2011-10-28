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
/System/Library/Frameworks/Accelerate.framework/Versions/A/Accelerate
/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit
/System/Library/Frameworks/Cocoa.framework/Versions/A/Cocoa
/usr/lib/libobjc.A.dylib
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

is_framework()
{
    echo $1 | grep -q '\.framework/'
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
# It is the dirname of that path.
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

    chrpath -r "$rpath" "$file" &>/dev/null || die "chrpath failed"
}


# Magic here:
# much like Linux's $ORIGIN, @executable_path is a runtime-determined value...
# except that it always points to $(dirname BINARY) that caused the load, not the
# library (if it is one)
set_rpath_darwin() {
    local file="$1"
    local root="$2"
    shift 2
    local dir="$(dirname $file)"

    # This is the library's name for itself (equiv to soname in linux, except
    # it has full path)
    local myname=$(otool -D $file | tail -n1)

    # Skip the first line of otool, which is the header
    otool -L $file | awk 'NR > 1 {print $1}' | while read entry; do

        # Don't warn me about things I know I'm skipping
        if is_whitelist $entry; then
            continue
        fi

        # /tmp/build/install/lib/libvwCore.5.dylib
        # base = libvwCore.5.dylib
        # looks for @executable_path/../lib/libvwCore.5.dylib

        # /opt/local/libexec/qt4-mac/lib/QtXml.framework/Versions/4/QtXml
        # base = QtXml.framework/Versions/4/QtXml
        # looks for @executable_path/../lib/QtXml.framework/Versions/4/QtXml

        local base=""
        if is_framework $entry; then
            local fprefix="$(dirname ${entry%%.framework/*})"
            base="${entry#${fprefix}/}"
        else
            base="$(basename $entry)"
        fi


        # OSX rpath points to one specific file, not anything that matches the
        # library SONAME. Therefore, do the library discovery right now, rather
        # than delaying until runtime like in Linux
        local new=""
        for rpath in "$@"; do
            if [[ -r "${dir}/${root}/$rpath/$base" ]]; then
                # This code assumes that the binaries are installed at $DISTDIR/bin
                new="@executable_path/../$rpath/$base"
            fi
        done
        if [[ -n $new ]]; then
            # If the entry is the "self" one, it has to be changed differently
            if [[ "$entry" = "$myname" ]]; then
                install_name_tool -id $new $file || die "FAILED: install_name_tool -id $new $file"
            else
                install_name_tool -change $entry $new $file || die "FAILED: install_name_tool -change $entry $new $file"
            fi
        else
            echo "ERROR: Skipped $file: $entry"
        fi
    done
}

# This takes 2 arguments:
# The first is the file (binary or library) to set rpath on
# The second is the path from $(dirname $file) to the root of the dist
set_rpath() {
    case $(getOS) in
        Linux) set_rpath_linux $* ;;
        OSX)   set_rpath_darwin $* ;;
        *) die "Unknown OS: $(getOS)"
    esac
}

do_strip_darwin() {
    local file="$1"
    strip -S $file
}

STRIP_FLAGS_SAFE="--strip-unneeded"
STRIP_FLAGS="${STRIP_FLAGS_SAFE} -R .comment"

inode_var_name() {
    stat -c 'INODE_%d_%i' "$1"
}

#save_elf_sources() {
#    type -P debugedit >/dev/null || return 0
#
#    local file="$1"
#    local inode=$(inode_var_name "$x")
#    [[ -n ${!inode} ]] && return 0
#    debugedit -b "${WORKDIR}" -d "${prepstrip_sources_dir}" \
#        -l "${T}"/debug.sources "${x}"
#}

unset ${!INODE_*}

save_elf_debug() {
    local file="$1"
    local debug="$(dirname $file)/$(basename $file).debug"

    # dont save debug info twice
    [[ $file == *".debug" ]] && return 0

    local inode=$(inode_var_name "$file")

    if [[ -n ${!inode} ]] ; then
        ln "$(dirname $debug)/${!inode}.debug" "$debug"
    else
        eval $inode=\$file
        objcopy --only-keep-debug "$file" "$debug"
        objcopy --add-gnu-debuglink="$debug" "$file"
    fi
}

do_strip_linux() {
    local file="$1"

    # Okay, first, try to save debug information!
    local type=$(file "$file")

    if [[ -z $type ]]; then
        strip -g "$file"
    elif [[ $type == *"current ar archive"* ]] ; then
        strip -g "$file"
    elif [[ $type == *"SB executable"* || $type == *"SB shared object"* ]] ; then
        #save_elf_sources "$file"
        save_elf_debug "$file"
        strip $STRIP_FLAGS "$file"
    elif [[ $type == *"SB relocatable"* ]] ; then
        #save_elf_sources "$file"
        strip $STRIP_FLAGS_SAFE "$file"
    fi
}

# This takes 1 argument: the binary or library to strip
do_strip() {
    case $(getOS) in
        Linux) do_strip_linux $* ;;
        OSX)   do_strip_darwin $* ;;
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

# Keep this in sync with the function in libexec-funcs.sh
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
