#!/bin/bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$repo"
[ "$#" -eq 1 ] || { echo 'Specify packages, runtimes, vim, or shell.' >&2; exit 2; }

install_xcodes_release() (
    set -euo pipefail
    command -v xcodes >/dev/null 2>&1 && exit 0

    version='2.1.0'
    sha256='f1519afe934a513e85dd9b32fc872394becbbb6a41db15d9ac3926a09a891888'
    url="https://github.com/XcodesOrg/xcodes/releases/download/$version/xcodes.zip"
    tmp=$(mktemp -d -t xcodes-release)
    trap 'rm -rf "$tmp"' EXIT

    curl --fail --show-error --silent --location "$url" -o "$tmp/xcodes.zip"
    printf '%s  %s\n' "$sha256" "$tmp/xcodes.zip" | shasum -a 256 -c - >/dev/null
    mkdir -p "$tmp/extracted"
    ditto -x -k "$tmp/xcodes.zip" "$tmp/extracted"

    binary=$(find "$tmp/extracted" -type f -name xcodes -perm +111 -print -quit)
    [ -n "$binary" ] || { echo 'xcodes release archive did not contain an executable.' >&2; exit 1; }
    install -m 0755 "$binary" "$(brew --prefix)/bin/xcodes"
)

case "$1" in
    packages)
        command -v brew >/dev/null || { echo 'Run ./install.sh first.' >&2; exit 1; }
        install_xcodes_release
        brew bundle install --no-upgrade --file="$repo/.Brewfile"
        ;;
    runtimes)
        # Use only the reviewed runtime manifest, independent of the caller's project.
        mise trust "$repo/.config/mise/config.toml"
        mise -C "$repo/.config/mise" install
        ;;
    vim)
        destination="$HOME/.vim/bundle/Vundle.vim"
        if [ ! -e "$destination" ]; then
            git clone https://github.com/VundleVim/Vundle.vim.git "$destination"
        elif [ ! -f "$destination/autoload/vundle.vim" ]; then
            echo "Unexpected contents at $destination; inspect them before continuing." >&2; exit 1
        fi
        vim -Nu "$repo/.vimrc" -n -es '+PluginInstall --sync' '+qa'
        ;;
    shell)
        fish_path="$(brew --prefix)/bin/fish"
        [ -x "$fish_path" ] || { echo 'Install fish first.' >&2; exit 1; }
        if ! /usr/bin/grep -Fxq "$fish_path" /etc/shells; then
            printf '%s\n' "$fish_path" | sudo tee -a /etc/shells >/dev/null
        fi
        current_shell=$(dscl . -read "/Users/$(id -un)" UserShell | sed 's/^UserShell: //')
        if [ "$current_shell" != "$fish_path" ]; then chsh -s "$fish_path"; fi
        echo 'Open a new terminal to use fish.'
        ;;
    *) echo 'Unknown setup stage.' >&2; exit 2 ;;
esac
