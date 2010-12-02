#!/bin/bash

set -e

if [[ $# -gt 0 ]]; then
    VERSION="$1"
    shift 1
fi

self=$$
source ./funcs.sh

# Need GNU coreutils
export PATH="$HOME/local/coreutils/bin:$PATH"

if ! ls --version >/dev/null; then
    die "Need gnu coreutils"
fi

if [[ -n $VERSION ]]; then
    BUILDNAME=StereoPipeline-${VERSION}-$(uname -m)-$(getOS)
else
    BUILDNAME=StereoPipeline-$(uname -m)-$(getOS)-$(date +"%Y-%m-%d_%H-%M-%S")
fi

INSTALL_DIR=/tmp/build/install
# Must be an absolute path
DIST_DIR=/tmp/build/${BUILDNAME}

BINS="              \
  bundlevis         \
  cam2map4stereo.py \
  disparitydebug    \
  hiedr2mosaic.py   \
  hsv_merge         \
  isis_adjust       \
  orbitviz          \
  orthoproject      \
  point2dem         \
  point2mesh        \
  stereo            \
  stereo_corr       \
  stereo_fltr       \
  stereo_pprc       \
  stereo_rfne       \
  stereo_tri        \
  colormap          \
  hillshade         \
  image2qtree       \
  ipfind            \
  ipmatch           \
  osgviewer         \
"

obin="${DIST_DIR}/bin"
olibexec="${DIST_DIR}/libexec"
olib="${DIST_DIR}/lib"

ibin="${INSTALL_DIR}/bin"
ilib="${INSTALL_DIR}/lib"
idoc="${INSTALL_DIR}/share/doc/StereoPipeline"

rm -rf ${DIST_DIR}

mkdir -p $obin $olib $olibexec
for i in ${BINS}; do
    cp -av $ibin/$i $olibexec/;
    cp libexec-helper.sh $obin/$i
done

rsync -am --delete --include='*.so*' --include='*.dylib*' --include='*/' --exclude='*' $ilib/ $olib/

for i in $olibexec/* $(find $olib -type f \( -name '*.dylib*' -o -name '*.so*' \) ); do
    if [[ -f $i ]]; then
        echo "Processing $i"
        # root is the relative path from the object in question to the top of
        # the dist
        root="$(get_relative_path ${DIST_DIR} $i)"
        [[ -z "$root" ]] && die "failed to get relative path to root"

        case $i in
            *.py) echo "Skipping python script $i";;
            */stereo) echo "Skipping python script without .py $i";;
            *)
            # The rpaths given here are relative to the $root
            set_rpath $i $root ../isis/lib ../isis/3rdParty/lib lib || die "set_rpath failed"
            do_strip $i || die "Could not strip $i"
        esac
    fi
done

if [[ $(getOS) == Linux ]]; then
    ldd "${olib}/libaspCore.so" | grep 'lib\(stdc++\|gcc_s\)' | awk '{print $3}' | xargs cp -v -t ${olib}
fi

if [[ -d dist-add ]]; then
    (cd dist-add && cp -aLv --parents . ${DIST_DIR})
fi

if [[ -d $idoc ]]; then
    (cd $idoc && cp -aLv --parents . ${DIST_DIR})
fi

find ${DIST_DIR} -name .svn -print0 | xargs -0 rm -rf

TOPLEVEL=$(cd ${DIST_DIR}/.. && pwd)

chmod +x ${TOPLEVEL}/${BUILDNAME}/libexec/* ${TOPLEVEL}/${BUILDNAME}/bin/*

set -x
(cd ${TOPLEVEL} && find ${BUILDNAME} -name '*.debug') > ${BUILDNAME}.dlist

tar czf ${BUILDNAME}.tar.gz        -X ${BUILDNAME}.dlist -C ${TOPLEVEL} ${BUILDNAME}
if test -s ${BUILDNAME}.dlist; then
    tar czf ${BUILDNAME}-debug.tar.gz  -T ${BUILDNAME}.dlist -C ${TOPLEVEL} ${BUILDNAME} --no-recursion
fi
