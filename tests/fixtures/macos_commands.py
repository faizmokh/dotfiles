#!/usr/bin/python3
"""Test-only commands: never touch the user's CFPreferences domain."""
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import sys

command = Path(sys.argv[0]).name
args = sys.argv[1:]
state = Path(os.environ['DOTS_PREFERENCES'])
if command == 'pgrep':
    sys.exit(0 if Path(os.environ['DOTS_XCODE_RUNNING']).exists() else 1)
if command == 'defaults':
    values = json.loads(state.read_text())
    if args[0] == 'export':
        sys.stdout.buffer.write(plistlib.dumps(values))
    elif args[0] == 'domains':
        print('com.apple.dt.Xcode')
    elif args[0] == 'write':
        parsers = {'-bool': lambda value: value == 'true', '-int': int, '-float': float, '-string': str}
        values[args[2]] = parsers[args[3]](args[4])
        state.write_text(json.dumps(values))
    elif args[0] == 'delete':
        del values[args[2]]
        state.write_text(json.dumps(values))
    else:
        sys.exit('Unsupported defaults test operation')
elif command == 'mise':
    if 'macos' in args and 'defaults' in args:
        if '--dry-run' in args:
            print('Would apply Xcode defaults (test backend).')
        else:
            repo = Path(os.environ['DOTS_FIXTURE_REPO'])
            spec = importlib.util.spec_from_file_location('xcode', repo / 'scripts/xcode-settings.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            values = json.loads(state.read_text())
            values.update(module.desired())
            state.write_text(json.dumps(values))
    else:
        os.execv(os.environ['DOTS_REAL_MISE'], [os.environ['DOTS_REAL_MISE']] + args)
else:
    sys.exit('Unexpected test command')
