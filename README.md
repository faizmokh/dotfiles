# ·

There's many like this but this is mine.

## Set up dotfiles on a new machine

Run in Terminal:

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/faizmokh/dotfiles/master/install.sh)"
```

Follow the prompts.

## Daily use

```sh
dots status
dots apply --dry-run
dots apply
dots doctor
```

Quit Xcode before applying. Use `dots setup` to rerun setup and `dots help` for
all commands.

## Save changes

```sh
dots diff
dots add .config/fish/config.fish
dots diff --staged
dots push
```

`dots push` auto-commits staged changes with a timestamp. Stage named files only. Use `dots pull` to update a clean checkout.
Pi settings live in `~/.pi`; use `dots pi status`, `diff`, `add`, `commit`, `pull`,
and `push` to manage them separately.

## Xcode settings

Includes Catppuccin Latte, Dracula Maple, keybindings, and editor settings.
Quit Xcode before saving local edits:

```sh
# Copy your current Xcode setup into the dotfiles repo (does not stage changes)
dots capture xcode
dots diff
```

Review and commit the changed files. Applying dotfiles backs up changed live
preferences first. To roll those preferences back into Xcode:

```sh
# Copy a backup into Xcode (preferences only; does not restore files)
dots restore xcode /absolute/path/to/backup.json
```

## Update tools

Run from the repo:

```sh
# After editing .Brewfile (including Mac App Store apps):
mise run setup:packages

# After editing versions in .config/mise/config.toml:
mise run setup:runtimes
```

Projects can set their own runtime versions. Keep private settings in
`~/.gitconfig.local` and `~/.config/fish/local.fish`.
