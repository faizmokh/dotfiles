source $(brew --prefix)/share/antigen/antigen.zsh

antigen use oh-my-zsh

# Bundles
antigen bundle git
antigen bundle gem
antigen bundle osx

antigen bundle zsh-users/zsh-syntax-highlighting

# Themes
antigen theme robbyrussell

# Tell antigen that we're done
antigen apply

# Alias
alias config='/usr/local/bin/git --git-dir=$HOME/.cfg --work-tree=$HOME'
