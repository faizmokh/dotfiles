#!/bin/bash
set -uo pipefail
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$repo"
failed=0
check() {
    label=$1; shift
    if "$@"; then printf 'DONE   %s\n' "$label"; else printf 'FAILED %s\n' "$label" >&2; failed=1; fi
}
reminder() {
    label=$1; shift
    if ! "$@"; then printf 'NEXT   %s\n' "$label"; fi
}
wezterm_config() { wezterm --config-file "$repo/.config/wezterm/wezterm.lua" show-keys --lua >/dev/null; }
for tool in brew fish mise git git-lfs wezterm lazygit opencode; do
    check "$tool available" command -v "$tool"
done
reminder 'Install xcodes later to manage Xcode versions' command -v xcodes
check 'Managed dotfiles' mise -C "$repo" dotfiles status --missing
check 'Pi configuration checkout' /usr/bin/python3 "$repo/scripts/piconf.py" status
reminder 'Apply Xcode preference values after Xcode setup' /usr/bin/python3 "$repo/scripts/xcode-settings.py" check
check 'WezTerm config' wezterm_config
check 'Declared Homebrew packages' brew bundle check --file="$repo/.Brewfile"
check 'Mise configuration' mise doctor
check 'Fish syntax' fish --no-config -n "$repo/.config/fish/config.fish"
missing=$(mise -C "$repo/.config/mise" ls --missing --no-header 2>&1)
if [ "$?" -ne 0 ] || [ -n "$missing" ]; then
    printf 'FAILED runtime installation\n%s\n' "$missing" >&2; failed=1
else
    echo 'DONE   pinned runtimes installed'
fi
reminder 'Install and select Xcode later' xcodebuild -version
check 'Vundle installed' test -f "$HOME/.vim/bundle/Vundle.vim/autoload/vundle.vim"
reminder 'Install Android platform tools in Android Studio' test -x "$HOME/Library/Android/sdk/platform-tools/adb"
reminder 'Install Android command-line tools in Android Studio' test -x "$HOME/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager"
reminder 'Review Android licenses with sdkmanager --licenses' test -d "$HOME/Library/Android/sdk/licenses"
check 'Flutter SDK installed' mise -C "$repo/.config/mise" where flutter
check 'Pi CLI installed' mise -C "$repo/.config/mise" where npm:@earendil-works/pi-coding-agent
echo 'NEXT   Run flutter doctor manually after SDK installation; it can initialize caches/download artifacts.'
echo 'NEXT   enable Hammerspoon Accessibility permission and use /login in Pi when needed.'
exit "$failed"
