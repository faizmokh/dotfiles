#!/bin/bash
set -euo pipefail
[ "$#" -le 1 ] || { echo 'Usage: mise run setup:xcode [-- "<version>"]' >&2; exit 2; }
if [ "$#" -eq 1 ]; then
    case "$1" in [0-9]*) ;; *) echo 'Specify an Xcode version, not an option.' >&2; exit 2 ;; esac
    xcodes install "$1"
    xcodes select "$1"
elif ! xcodebuild -version >/dev/null 2>&1; then
    xcodes install --latest --select
else
    echo 'Reusing the selected Xcode.'
fi
if ! xcodebuild -checkFirstLaunchStatus >/dev/null 2>&1; then
    sudo xcodebuild -runFirstLaunch
fi
xcodebuild -version
