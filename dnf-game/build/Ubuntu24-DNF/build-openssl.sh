#!/bin/sh
set -eu
cd /tmp/openssl
./config shared no-ssl2 no-ssl3 --prefix=/opt/dnf/openssl098
# Preserve the genuine 0.9.8 ABI while matching this gateway's historical SONAME.
sed -i 's/^SHLIB_EXT=.*/SHLIB_EXT=.so.6/; s/LIBVERSION=${SHLIB_MAJOR}.${SHLIB_MINOR}/LIBVERSION=6/g' Makefile
make -j1 >/tmp/openssl-build.log 2>&1 || { tail -100 /tmp/openssl-build.log; exit 1; }
