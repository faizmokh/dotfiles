"""Xcode mappings come from mise, the single source of file ownership."""
import json
import os
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[1]
USER_DATA = Path.home() / 'Library/Developer/Xcode/UserData'
LEGACY_THEMES = (
    'Cappucino', 'Catppuccin Latte', 'Default (Light) Maple', 'Default (Light)',
    'Dracula Maple', 'Dracula', 'High Contrast (Dark) 2', 'Midnight 2', 'Mocha', 'Spartan',
)


def mappings():
    result = subprocess.run(['mise', '-C', str(REPO), 'dotfiles', 'status', '--json'],
                            text=True, stdout=subprocess.PIPE, check=True)
    entries = []
    for entry in json.loads(result.stdout)['files']:
        target = Path(entry['target']).expanduser()
        try:
            relative = target.relative_to(USER_DATA)
        except ValueError:
            continue
        source = Path(entry['source'])
        if (entry['mode'] != 'symlink' or len(relative.parts) != 2 or
                (relative.parts[0], relative.suffix) not in
                [('FontAndColorThemes', '.xccolortheme'), ('KeyBindings', '.idekeybindings')] or
                REPO / 'xcode' not in source.resolve().parents):
            raise ValueError('Unexpected Xcode mapping: ' + str(target))
        entries.append((source, target))
    if not entries:
        raise ValueError('No Xcode file mappings declared in mise.toml.')
    return entries


def legacy_links():
    relatives = ['FontAndColorThemes/' + name + '.xccolortheme' for name in LEGACY_THEMES]
    relatives.append('KeyBindings/Default.idekeybindings')
    for relative in relatives:
        target = USER_DATA / relative
        # Never follow a user-owned directory symlink to remove a file elsewhere.
        parents = []
        for parent in target.parents:
            if parent == Path.home():
                break
            parents.append(parent)
        if any(parent.is_symlink() for parent in parents):
            continue
        if target.is_symlink():
            link = Path(os.path.abspath(target.parent / os.readlink(target)))
            # Resolve only the parent, so dangling links remain identifiable.
            link = link.parent.resolve() / link.name
            if link == REPO / 'xcode' / relative:
                yield target


def cleanup(dry_run=False):
    for target in legacy_links():
        print(('Would remove' if dry_run else 'Removing') + ' old checkout-owned link: ' + str(target))
        if not dry_run:
            target.unlink()


if __name__ == '__main__':
    import sys
    if sys.argv[1:] not in ([], ['--dry-run']):
        sys.exit('Usage: xcode_files.py [--dry-run]')
    cleanup(bool(sys.argv[1:]))
