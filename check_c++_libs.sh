# This is a simple script to help find any libraries that link to an offending library.
# - The main use is to identify libstdc++ usage on OSX which will cause run-time crashes.

for f in build_asp/install/lib/*.dylib
do
  echo $f
  otool -L $f | grep libstdc++
done
