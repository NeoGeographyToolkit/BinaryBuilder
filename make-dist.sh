#!/bin/bash

# Need GNU coreutils
export PATH="$HOME/local/coreutils/bin:$PATH"

self=$$
source ./funcs.sh

BUILDNAME=stereopipeline-$(uname -s | tr A-Z a-z)-$(uname -m)-$(date +"%Y-%m-%d_%H-%M-%S")

INSTALL_DIR=/tmp/build/install
DIST_DIR=/tmp/build/${BUILDNAME}

BINS="bundle_adjust bundlevis colormap disparitydebug hillshade image2qtree ipfind ipmatch isis_adjust orbitviz point2dem point2mesh stereo"

obin="${DIST_DIR}/bin"
olib="${DIST_DIR}/lib"

ibin="${INSTALL_DIR}/bin"
ilib="${INSTALL_DIR}/lib"

rm -rf ${DIST_DIR}

mkdir -p $obin $olib
for i in ${BINS}; do cp -av $ibin/$i $obin/; done
for i in $ilib/*.$(shared_name)*; do cp -av $i $olib/; done

for i in $obin/* $olib/*; do
    if [[ -f $i ]]; then
        set_rpath $i ../../isis/lib ../../isis/3rdParty/lib ../lib || die "set_rpath failed"
        strip -S $i || die "Could not strip $i"
    fi
done

if [[ $(getOS) == Linux ]]; then
    ldd "${olib}/libaspCore.so" | grep 'lib\(stdc++\|gcc_s\)' | awk '{print $3}' | xargs cp -v -t ${olib}
fi

tar czf ${BUILDNAME}.tar.gz  -C ${DIST_DIR}/.. ${BUILDNAME}
