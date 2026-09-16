#!/bin/bash
set -euo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$repo"
[ "$#" -eq 1 ] || { echo 'Specify packages, runtimes, vim, or shell.' >&2; exit 2; }
case "$1" in
    packages)
        command -v brew >/dev/null || { echo 'Run ./install.sh first.' >&2; exit 1; }
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
