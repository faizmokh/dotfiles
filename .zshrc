source $(brew --prefix)/share/antigen/antigen.zsh

antigen use oh-my-zsh

# Bundles
antigen bundle git
antigen bundle gem
antigen bundle osx

antigen bundle zsh-users/zsh-syntax-highlighting

# Themes
antigen theme faizmokhtar/zkrang themes/zkrang
# antigen theme robbyrussell

# Tell antigen that we're done
antigen apply

# Alias
alias config='/usr/local/bin/git --git-dir=$HOME/.cfg --work-tree=$HOME'

# Load rbenv
eval "$(rbenv init -)"

# Load z
. `brew --prefix`/etc/profile.d/z.sh

# Load nvm
export NVM_DIR="$HOME/.nvm"
. "/usr/local/opt/nvm/nvm.sh"

# Load yarn
export PATH="$PATH:`yarn global bin`"
