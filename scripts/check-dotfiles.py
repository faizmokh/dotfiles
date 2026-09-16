#!/usr/bin/python3
"""Read mise's manifest; refuse adoption before mise makes any links.

Mise can repoint an existing symlink without --force. The dots interface is
stricter: all existing targets must already be ours. Back up conflicts manually.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from xcode_files import legacy_links

repo = Path(__file__).resolve().parents[1]
result = subprocess.run(["mise", "-C", str(repo), "dotfiles", "status", "--json"],
                        stdout=subprocess.PIPE, text=True)
if result.returncode:
    sys.exit(result.returncode)
manifest = json.loads(result.stdout)
conflicts = set()
home = Path.home()
legacy = set(legacy_links())


def check_parents(target):
    for parent in target.parents:
        if parent == home:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            conflicts.add(str(parent))


def check_link(target, source):
    check_parents(target)
    if target.is_symlink():
        if target.resolve() != source.resolve() and target not in legacy:
            conflicts.add(str(target))
    elif target.exists():
        conflicts.add(str(target))


for entry in manifest["files"]:
    target = Path(entry["target"]).expanduser()
    source = Path(entry["source"])
    if entry["mode"] == "symlink":
        check_link(target, source)
    elif entry["mode"] == "symlink-each":
        check_parents(target)
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            conflicts.add(str(target))
        for directory, dirs, files in os.walk(source):
            for name in files:
                child = Path(directory) / name
                check_link(target / child.relative_to(source), child)
    else:
        sys.exit("dots: only symlink and symlink-each entries are supported by the adoption guard.")
if manifest.get("edits"):
    sys.exit("dots: edit entries require a reviewed adoption policy before use.")
if conflicts:
    print("dots: back up and move these conflicting paths before applying:", file=sys.stderr)
    for path in sorted(conflicts):
        print("  " + path, file=sys.stderr)
    sys.exit(1)
