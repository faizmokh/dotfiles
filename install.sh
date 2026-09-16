#!/bin/bash
# This file also runs through /bin/bash -c on a Mac with no Git or mise yet.
set -euo pipefail
# Keep this display self-contained: the remote bootstrap runs before cloning.
started=$SECONDS
stage_started=$SECONDS
stage_number=0
completed=0
stage='Startup'
recovery='Review the error above.'
report() {
    local label=$1 color=''
    shift
    if [ -t 1 ] && [ "${NO_COLOR+x}" != x ] && [ "${TERM:-dumb}" != dumb ]; then
        case "$label" in
            RUN) color='36' ;; DONE) color='32' ;; FAILED) color='31' ;; *) color='33' ;;
        esac
        printf '\033[%sm%-6s\033[0m %s\n' "$color" "$label" "$*"
    else
        printf '%-6s %s\n' "$label" "$*"
    fi
}
begin_stage() {
    stage_number=$((stage_number + 1))
    stage=$1
    recovery=$2
    stage_started=$SECONDS
    printf '\n'
    report RUN "[$stage_number/15] $stage"
}
finish_stage() {
    completed=$((completed + 1))
    report DONE "[$stage_number/15] $stage ($((SECONDS - stage_started))s)"
}
failed() {
    local code=$1
    trap - ERR INT TERM
    if [ "$code" -eq 130 ] || [ "$code" -eq 143 ]; then
        report FAILED "[$stage_number/15] $stage interrupted after $((SECONDS - stage_started))s (exit $code)." >&2
    else
        report FAILED "[$stage_number/15] $stage failed after $((SECONDS - stage_started))s (exit $code)." >&2
    fi
    report INFO "$completed/15 stages completed; total elapsed $((SECONDS - started))s." >&2
    report NEXT "$recovery Then rerun setup." >&2
    exit "$code"
}
trap 'failed $?' ERR
trap 'failed 130' INT
trap 'failed 143' TERM
fail() { report FAILED "$1" >&2; failed "${2:-1}"; }

cat <<'BANNER'

     _       _
  __| | ___ | |_ ___
 / _` |/ _ \| __/ __|
| (_| | (_) | |_\__ \
 \__,_|\___/ \__|___/

macOS setup
BANNER
report INFO '15 stages. Follow password, license, and Apple sign-in prompts.'
begin_stage 'Platform' 'Use an Apple Silicon Mac outside Rosetta.'
[ "$#" -eq 0 ] || fail 'The installer takes no arguments.'
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || fail 'Apple Silicon macOS is required; run outside Rosetta.'

finish_stage
begin_stage 'Command Line Tools' 'Complete the Command Line Tools installer.'
if ! xcode-select -p >/dev/null 2>&1; then
    xcode-select --install
    report INFO 'Finish the macOS installer. Waiting up to 20 minutes; Ctrl+C cancels.'
    attempts=0
    until xcode-select -p >/dev/null 2>&1; do
        [ "$attempts" -lt 120 ] || fail 'Command Line Tools are still unavailable after 20 minutes. Finish installation and rerun.'
        sleep 10
        attempts=$((attempts + 1))
        if [ "$((attempts % 3))" -eq 0 ]; then
            report INFO "Waiting for Command Line Tools ($((attempts * 10))s)."
        fi
    done
else
    report INFO 'Reusing installed Command Line Tools.'
fi
finish_stage

begin_stage 'Homebrew' 'Fix the Homebrew error above.'
if [ ! -x /opt/homebrew/bin/brew ]; then
    installer=$(mktemp -t dots-homebrew)
    trap 'rm -f "$installer"' EXIT
    curl --fail --show-error --silent --location https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer"
    /bin/bash "$installer"
else
    report INFO 'Reusing installed Homebrew.'
fi
brew_environment=$(/opt/homebrew/bin/brew shellenv bash)
eval "$brew_environment"
finish_stage
begin_stage 'Prerequisites' 'Fix the tool installation error above.'
brew install git fish mise
mise dotfiles --help >/dev/null

finish_stage
begin_stage 'Checkout' 'Check the repo path and origin; keep local files.'
script=${BASH_SOURCE[0]:-}
if [ -n "$script" ] && [ -f "$script" ] && [ -f "$(dirname "$script")/mise.toml" ]; then
    repo=$(cd -P "$(dirname "$script")" && pwd)
else
    repo="$HOME/Developer/dotfiles"
fi
if [ ! -e "$repo" ]; then
    mkdir -p "$(dirname "$repo")"
    git clone https://github.com/faizmokh/dotfiles.git "$repo"
else
    report INFO "Verifying existing checkout: $repo (no pull or reset)."
fi
[ ! -L "$repo" ] || fail 'The checkout path is a symlink; inspect it before setup.'
root=$(git -C "$repo" rev-parse --show-toplevel) || fail 'The target must be a dotfiles Git checkout.' "$?"
[ "$(cd -P "$root" && pwd)" = "$(cd -P "$repo" && pwd)" ] || fail 'The target is inside another repository.'
origin=$(git -C "$repo" config --get-all remote.origin.url) || fail 'The checkout needs the expected origin.' "$?"
case "$origin" in
    https://github.com/faizmokh/dotfiles|https://github.com/faizmokh/dotfiles.git|git@github.com:faizmokh/dotfiles|git@github.com:faizmokh/dotfiles.git|ssh://git@github.com/faizmokh/dotfiles|ssh://git@github.com/faizmokh/dotfiles.git) ;;
    *) fail 'Unexpected checkout origin; expected faizmokh/dotfiles on GitHub.' ;;
esac
cd "$repo"
finish_stage
begin_stage 'Trust' 'Check the mise config error above.'
mise trust "$repo/mise.toml"
mise trust "$repo/.config/mise/config.toml"
# Make runtimes available to this noninteractive bootstrap before fish starts.
mise_environment=$(mise activate bash --shims)
eval "$mise_environment"
finish_stage

# Fail before expensive setup work; dots apply repeats this guard before mutation.
begin_stage 'Dotfile conflicts' 'Back up and move any reported conflicting files.'
/usr/bin/python3 "$repo/scripts/check-dotfiles.py"
finish_stage

# Run each task directly so the active heading identifies failures precisely.
tasks=(setup:packages setup:runtimes setup:pi setup:vim setup:xcode setup:dotfiles setup:shell doctor)
labels=('Packages' 'Runtimes' 'Pi' 'Vim' 'Xcode' 'Dotfiles' 'Login shell' 'Diagnostics')
recoveries=(
    'Fix the package error above.'
    'Fix the runtime error above.'
    'Check the Pi repo and keep local changes.'
    'Check the Vim error and network connection.'
    'Complete Apple authentication or fix the Xcode error.'
    'Quit Xcode; back up and move any reported conflicting files.'
    'Check fish and login-shell permissions.'
    'Fix the failed checks above.'
)
for index in "${!tasks[@]}"; do
    begin_stage "${labels[$index]}" "${recoveries[$index]}"
    mise -C "$repo" run --skip-tools "${tasks[$index]}"
    finish_stage
done
printf '\n'
report DONE "Setup complete: $completed/15 stages in $((SECONDS - started))s."
report NEXT 'Open WezTerm to use fish.'
report NEXT 'Android: install SDK tools, accept licenses, then run flutter doctor.'
report NEXT 'Pi: run pi, then /login.'
report NEXT 'Allow Hammerspoon Accessibility access.'
