#!/bin/sh

self=$$
trap 'exit 1' TERM

# This if a fix for ASP being called from within an incompatible conda environment.
unset GDAL_DRIVER_PATH
unset PDAL_DRIVER_PATH
unset GDAL_DATA
unset PROJ_DATA
unset PROJ_LIB

# Care here if the paths have spaces
EXEC_PATH="$0"
DIR_NAME=$(dirname "$EXEC_PATH")
EXEC_NAME=$(basename "$EXEC_PATH")
TOPLEVEL=$(cd "$DIR_NAME"/..; echo "$(pwd)")

if [ "$ASP_DEBUG_DIR" != "" ]; then
    LIBEXEC="$ASP_DEBUG_DIR"
else
    LIBEXEC="${TOPLEVEL}/libexec"
fi
    
export ISISROOT="$TOPLEVEL"
#export ALESPICEROOT="$ISISDATA" # TODO(oalexan1): Think of this.

. "${LIBEXEC}/constants.sh"
. "${LIBEXEC}/libexec-funcs.sh"

check_isis

if [ "$(uname -s)" = "Linux" ]; then
    check_libc
fi

# Find the path to the Tcl library. Careful with paths having spaces.
TCL_LIBRARY=$(cd "$TOPLEVEL"; tcl=$(find . -name init.tcl); tcl=$(dirname $tcl); cd $tcl; echo "$(pwd)")
export TCL_LIBRARY="$TCL_LIBRARY"

PROGRAM="${LIBEXEC}/${EXEC_NAME}"

# Path to USGS CSM plugins
export CSM_PLUGIN_PATH="${TOPLEVEL}/plugins/usgscsm"

if [ "$(echo $PROGRAM | grep sparse_disp)" != "" ] &&
    [ "$ASP_PYTHON_MODULES_PATH" != "" ]; then
    # For sparse_disp we must not use ASP's libraries,
    # as those don't play well with Python
    export PYTHONPATH="$ASP_PYTHON_MODULES_PATH"
    # Also use the right Python
    # Careful with spaces in $ASP_PYTHON_MODULES_PATH
    dir1=$(dirname "$ASP_PYTHON_MODULES_PATH");  dir2=$(dirname "$dir1"); dir3=$(dirname "$dir2")
    export PATH="$dir3/bin":"$PATH"
    case $(uname -s) in
        Linux)
        export LD_LIBRARY_PATH="$ASP_PYTHON_MODULES_PATH"
        ;;
        Darwin)
        export DYLD_FALLBACK_LIBRARY_PATH="$ASP_PYTHON_MODULES_PATH"
        export DYLD_FALLBACK_FRAMEWORK_PATH="$ASP_PYTHON_MODULES_PATH"
        ;;
        *)
        die "Unknown OS: $(uname -s)"
        ;;
    esac
else

    # Need this to use the Python we ship, to deal with the fact that ISIS
    # expects a full Python runtime.
    export PATH="${TOPLEVEL}/bin":"$PATH"
    export PYTHONHOME="${TOPLEVEL}"
    set_lib_paths "${TOPLEVEL}/lib"
fi

# Needed for stereo_gui to start quickly. (Likely the slowdown this
# fixes is due to some misconfigured path in some conda libraries or
# how we ship them.)
IS_STEREO_GUI=$(echo "$PROGRAM" |grep "stereo_gui")
if [ "$IS_STEREO_GUI" != "" ] && [ -f "/etc/fonts/fonts.conf" ]; then
    export FONTCONFIG_PATH=/etc/fonts
    export FONTCONFIG_FILE=fonts.conf
fi

if ! test -f "${PROGRAM}"; then
    msg "Could not find ${PROGRAM}"
    die "Is your Stereo Pipeline install incomplete?"
fi
exec "${PROGRAM}" "$@"
