# source $(brew --prefix)/share/antigen/antigen.zsh
source /opt/homebrew/share/antigen/antigen.zsh

antigen use oh-my-zsh

# Bundles
antigen bundle git
antigen bundle gem
antigen bundle osx
antigen bundle sublime-merge

antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle mafredri/zsh-async
antigen bundle sindresorhus/pure --branch=main

# Tell antigen that we're done
antigen apply

# Alias
alias config='/opt/homebrew/bin/git --git-dir=$HOME/.cfg --work-tree=$HOME'

# Load z
. `brew --prefix`/etc/profile.d/z.sh

# Load yarn
# export PATH="$PATH:`yarn global bin`"
# export PATH="/usr/local/sbin:$PATH"

# Load fastlane
export PATH="$HOME/.fastlane/bin:$PATH"

# Fix locale configuration
export LC_ALL="en_US.UTF-8"

# Set up $GOPATH
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin
export PATH="/usr/local/opt/mysql@5.7/bin:$PATH"

# The next line updates PATH for Netlify's Git Credential Helper.
if [ -f '/Users/faizmokhtar/.netlify/helper/path.zsh.inc' ]; then source '/Users/faizmokhtar/.netlify/helper/path.zsh.inc'; fi

# Setup ANDROID_HOME env variable
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools

# Setup Flutter SDK
export PATH="$PATH:$HOME/flutter/bin"

# alias
alias mongodb='mongod --config /usr/local/etc/mongod.conf'

export PATH="/usr/local/sbin:$PATH"

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/ad0502/google-cloud-sdk/path.zsh.inc' ]; then . '/Users/ad0502/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/ad0502/google-cloud-sdk/completion.zsh.inc' ]; then . '/Users/ad0502/google-cloud-sdk/completion.zsh.inc'; fi

# silence ruby 2.7.* warnings
export RUBYOPT='-W:no-deprecated -W:no-experimental'

# setup asdf
. /opt/homebrew/opt/asdf/libexec/asdf.sh

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /usr/local/bin/terraform terraform
