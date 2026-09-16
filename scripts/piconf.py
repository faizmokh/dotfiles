#!/usr/bin/python3
"""Provision only a missing piconf checkout; never update existing work."""
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
TARGET = Path.home() / '.pi'
ORIGINS = {'https://github.com/faizmokh/piconf', 'https://github.com/faizmokh/piconf.git',
           'git@github.com:faizmokh/piconf', 'git@github.com:faizmokh/piconf.git',
           'ssh://git@github.com/faizmokh/piconf', 'ssh://git@github.com/faizmokh/piconf.git'}


def git(*args):
    return subprocess.run(['git', '-C', str(TARGET), *args], text=True, capture_output=True)


def verify():
    if TARGET.is_symlink():
        raise ValueError('~/.pi is a symlink; inspect it before provisioning.')
    if not TARGET.is_dir():
        raise ValueError('Pi checkout missing. Run mise run setup:pi from the dotfiles checkout.')
    root = git('rev-parse', '--show-toplevel')
    if root.returncode or Path(root.stdout.strip()).resolve() != TARGET.resolve():
        raise ValueError('~/.pi must be its own piconf Git checkout; back up conflicting contents first.')
    origins = git('config', '--get-all', 'remote.origin.url')
    if origins.returncode or origins.stdout.strip() not in ORIGINS:
        raise ValueError('~/.pi has an unexpected origin; expected faizmokh/piconf on GitHub.')
    push_urls = git('config', '--get-all', 'remote.origin.pushurl')
    if push_urls.returncode == 0 and push_urls.stdout.strip() not in ORIGINS:
        raise ValueError('~/.pi has an unexpected origin push URL.')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('check', 'status', 'setup'):
        raise ValueError('Usage: piconf.py check|status|setup')
    action = sys.argv[1]
    if action == 'setup' and not TARGET.is_symlink() and (
            not TARGET.exists() or (TARGET.is_dir() and not any(TARGET.iterdir()))):
        subprocess.run(['mise', '-C', str(REPO), 'bootstrap', 'repos', 'apply'], check=True)
    verify()
    if action == 'setup':
        print('Pi checkout ready; existing files and local changes preserved. Start pi and use /login.')
    elif action == 'status':
        subprocess.run(['git', '-C', str(TARGET), 'status', '--short', '--branch'], check=True)


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        sys.exit('dots: ' + str(error))
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
