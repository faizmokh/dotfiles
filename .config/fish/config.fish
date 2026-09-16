# Homebrew must be available before mise or other integrations.
if test -x /opt/homebrew/bin/brew
    /opt/homebrew/bin/brew shellenv fish | source
end
for directory in /opt/homebrew/opt/postgresql@18/bin /opt/homebrew/opt/mysql@8.4/bin
    if test -d $directory
        fish_add_path --path --append $directory
    end
end
fish_add_path --path $HOME/.local/bin
for directory in $HOME/go/bin $HOME/.fastlane/bin
    if test -d $directory
        fish_add_path --path --append $directory
    end
end

set -gx LANG en_US.UTF-8
set -gx GOPATH $HOME/go
set -gx ANDROID_HOME $HOME/Library/Android/sdk
for directory in $ANDROID_HOME/emulator $ANDROID_HOME/platform-tools $ANDROID_HOME/cmdline-tools/latest/bin
    if test -d $directory
        fish_add_path --path --append $directory
    end
end

if status is-interactive
    if command -q mise
        mise activate fish | source
    end
    if command -q zoxide
        zoxide init fish | source
    end
else
    # Scripts get executable shims without interactive hooks.
    if test -d $HOME/.local/share/mise/shims
        fish_add_path --path $HOME/.local/share/mise/shims
    end
end

# Private, machine-specific additions are never tracked.
if test -f $HOME/.config/fish/local.fish
    source $HOME/.config/fish/local.fish
end
