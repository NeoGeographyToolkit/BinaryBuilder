#!/bin/bash

BUILDNAME=stereopipeline-$(uname -s | tr A-Z a-z)-$(date +"%Y-%m-%d")

self=$$

die() {
    echo "$1" >&2
    kill -s SIGTERM $self
}

INSTALL_DIR=/tmp/build/install
DIST_DIR=/tmp/build/${BUILDNAME}

BINS="image2qtree colormap slopemap hillshade ipmatch ipfind stereo orthoproject bundle_adjust orbitviz disparitydebug point2mesh point2dem ctximage bundlevis isis_adjust"

obin="${DIST_DIR}/bin"
olib="${DIST_DIR}/lib"

ibin="${INSTALL_DIR}/bin"
ilib="${INSTALL_DIR}/lib"


rm -rf ${DIST_DIR}

mkdir -p $obin $olib
for i in ${BINS}; do cp -av $ibin/$i $obin/; done
for i in $ilib/*.so*; do cp -av $i $olib/; done

for i in $obin/* $olib/*; do
    if [[ -f $i ]]; then
        chrpath -r '$ORIGIN/../../isis3/lib:$ORIGIN/../../isis3/3rdParty/lib:$ORIGIN/../lib' $i || die "chrpath failed"
    fi
done

ldd "${olib}/libaspCore.so" | grep 'lib\(stdc++\|gcc_s\)' | awk '{print $3}' | xargs cp -v -t ${olib}

tar czf ${BUILDNAME}.tar.gz  -C ${DIST_DIR}/.. ${BUILDNAME}
