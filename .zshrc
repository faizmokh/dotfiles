# source $(brew --prefix)/share/antigen/antigen.zsh
source /usr/local/share/antigen/antigen.zsh

antigen use oh-my-zsh

# Bundles
antigen bundle git
antigen bundle gem
antigen bundle osx

antigen bundle lukechilds/zsh-nvm
antigen bundle zsh-users/zsh-syntax-highlighting

# Themes
antigen theme sunrise

# Tell antigen that we're done
antigen apply

# Alias
alias config='/usr/local/bin/git --git-dir=$HOME/.cfg --work-tree=$HOME'
alias git=hub

# Load rbenv
eval "$(rbenv init -)"

# Load z
. `brew --prefix`/etc/profile.d/z.sh

# Load yarn
# export PATH="$PATH:`yarn global bin`"
# export PATH="/usr/local/sbin:$PATH"

# Load fastlane
export PATH="$HOME/.fastlane/bin:$PATH"

# Fix locale configuration
export LC_ALL="en_US.UTF-8"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Set up $GOPATH
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/Users/faizmokhtar/google-cloud-sdk/path.zsh.inc' ]; then source '/Users/faizmokhtar/google-cloud-sdk/path.zsh.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/Users/faizmokhtar/google-cloud-sdk/completion.zsh.inc' ]; then source '/Users/faizmokhtar/google-cloud-sdk/completion.zsh.inc'; fi
