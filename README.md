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
dots commit -m "Update fish config"
dots push
```

Stage named files only. Use `dots pull` to update a clean checkout.
Pi settings live in `~/.pi`; use `dots pi status`, `diff`, `add`, `commit`, `pull`,
and `push` to manage them separately.

## Xcode settings

Includes Catppuccin Latte, Dracula Maple, keybindings, and editor settings.
Quit Xcode before saving local edits:

```sh
dots capture xcode
dots diff
```

Review and commit the changed files. Apply backs up changed preferences. Restore
with `dots restore xcode /absolute/path/to/backup.json`.

## Update tools

Run from the repo:

```sh
# After editing .Brewfile:
mise run setup:packages

# After editing versions in .config/mise/config.toml:
mise run setup:runtimes
```

Projects can set their own runtime versions. Keep private settings in
`~/.gitconfig.local` and `~/.config/fish/local.fish`.
