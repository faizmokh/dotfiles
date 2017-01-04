# Faiz's dotfiles 📝

My dotfiles config.

## Setting Up

- `cd` to home folder
```
cd ~
```
- clone the dotfiles into a bare repository
```
git clone git@github.com:faizmokhtar/dotfiles.git $HOME/.cfg
```
- define `alias` in current shell session
```
alias config='/usr/bin/git --git-dir=$HOME/.cfg/ --work-tree=$HOME'
```
- checkout bare repository contents to `$HOME`
```
config checkout
```
- Set the flag `showUntrackedFiles` to `no`
```
config config --local status.showUntrackedFiles no
```

## Installing Brew & Common applications

- Install [Brew][2]
```
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```
- Run the following in `$HOME` directory
```
brew bundle --global
```
- Voila! 🎉

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
[2]:http://brew.sh/
