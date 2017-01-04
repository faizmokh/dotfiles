# Faiz's dotfiles 📝

My dotfiles config.

## Installation

1. `cd` to home folder
```
cd ~
```
2. clone the dotfiles into a bare repository
```
git clone git@github.com:faizmokhtar/dotfiles.git $HOME/.cfg
```
3. define `alias` in current shell session
```
alias config='/usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME'
```
4. checkout bare repository contents to `$HOME`
```
config checkout
```
5. Set the flag `showUntrackedFiles` to `no`
```
config config --local status.showUntrackedFiles no
```

## Commands

Moving on, you can use `config` commands as how you would use `git`. Eg;

```
config status
config add .zshrc
config commit -m "Update zsh config"
config push -u origin master
```

## References

I refer to this excellent [articles][1] written by Nicola Paolucci to manage my dotfiles.

[1]:https://developer.atlassian.com/blog/2016/02/best-way-to-store-dotfiles-git-bare-repo/

