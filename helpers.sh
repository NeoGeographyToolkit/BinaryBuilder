
bb_needed_libs() {
    file ${1:-.}/* | grep ELF | cut -d : -f 1 | xargs readelf -d | grep NEEDED | sed -e 's/.*\[//g' -e 's/\].*//g' | sort -u
}

bb_found_libs() {
    ldd ${1:-.}/*
}

bb_filter_found() {
    LC_ALL=C fgrep --color=auto -f ${1:?[expected needed lib file]} ${2:?[expected found lib file]} | sed -e 's/(0x00.*//g' | sort -u | less
}
