#!/usr/bin/python3
"""Installer subprocess doubles. State and effects stay in a temporary directory."""
import json
import os
from pathlib import Path
import signal
import shlex
import subprocess
import sys

name, args = Path(sys.argv[0]).name, sys.argv[1:]
base = Path(os.environ['INSTALL_TEST_BASE'])
state_file = base / 'installer-state.json'
state = json.loads(state_file.read_text())
with (base / 'installer-log.jsonl').open('a') as out:
    out.write(json.dumps([name] + args) + '\n')

def save():
    state_file.write_text(json.dumps(state))

if name == 'uname':
    print('Darwin' if args == ['-s'] else 'arm64')
elif name == 'xcode-select':
    if args == ['--install']:
        state['requested'] = True; save()
    elif state.get('clt'):
        print('/Library/Developer/CommandLineTools')
    else:
        sys.exit(1)
elif name == 'sleep':
    if os.environ.get('INSTALL_TEST_SIGNAL'):
        os.kill(os.getppid(), signal.SIGINT)
        sys.exit(130)
    if os.environ.get('INSTALL_TEST_INTERRUPT'):
        sys.exit(130)
    state['waits'] = state.get('waits', 0) + 1
    state['clt'] = state['waits'] >= int(os.environ.get('INSTALL_TEST_CLT_WAITS', '1'))
    save()
elif name == 'curl':
    target = Path(args[args.index('-o') + 1])
    prefix = base / 'brew'
    template = base / 'installer-bin/brew-template'
    target.write_text('mkdir -p ' + shlex.quote(str(prefix / 'bin')) + '\ncp ' +
                      shlex.quote(str(template)) + ' ' + shlex.quote(str(prefix / 'bin/brew')) +
                      '\nchmod +x ' + shlex.quote(str(prefix / 'bin/brew')) + '\n')
elif name in ['brew', 'brew-template']:
    if args[:1] == ['shellenv']:
        print('export PATH=' + shlex.quote(str(base / 'brew/bin') + ':' + os.environ['PATH']))
    elif args == ['--prefix']:
        print(base / 'brew')
elif name == 'git':
    if args[:2] == ['clone', 'https://github.com/faizmokh/dotfiles.git']:
        subprocess.run(['/usr/bin/git', 'clone', os.environ['INSTALL_TEST_SOURCE'], args[-1]], check=True)
        subprocess.run(['/usr/bin/git', '-C', args[-1], 'remote', 'set-url', 'origin', args[1]], check=True)
    else:
        os.execv('/usr/bin/git', ['/usr/bin/git'] + args)
elif name == 'mise':
    if 'run' in args:
        repo = Path(args[args.index('-C') + 1])
        task = args[-1]
        with (base / 'installer-log.jsonl').open('a') as out:
            out.write(json.dumps(['stage', task]) + '\n')
        if os.environ.get('INSTALL_TEST_FAIL_STAGE') == task:
            sys.exit(42)
        if os.environ.get('INSTALL_TEST_PROMPT') == task:
            assert sys.stdin.isatty(), 'Prompt lost terminal input'
            print('Fixture authentication prompt:', flush=True)
            assert input() == 'continue'
            print('Fixture authentication accepted', flush=True)
        if task == 'setup:xcode':
            sys.exit(subprocess.run(['/bin/bash', str(repo / 'scripts/xcode.sh')]).returncode)
        elif task == 'setup:shell':
            sys.exit(subprocess.run(['/bin/bash', str(repo / 'scripts/setup.sh'), 'shell']).returncode)
elif name == 'xcodes':
    if os.environ.get('INSTALL_TEST_AUTH_FAIL'):
        sys.exit(42)
    state['xcode'] = True; save()
elif name == 'xcodebuild':
    if args == ['-version']:
        if not state.get('xcode'): sys.exit(1)
        print('Xcode 27.0')
    elif args == ['-checkFirstLaunchStatus']:
        sys.exit(0 if state.get('first_launch') else 1)
    elif args == ['-runFirstLaunch']:
        state['first_launch'] = True; save()
elif name == 'sudo':
    if args[0] == 'tee':
        assert Path(args[-1]) == base / 'shells'
        with (base / 'shells').open('a') as out: out.write(sys.stdin.read())
    elif args[0] == 'xcodebuild':
        os.execv(str(base / 'installer-bin/xcodebuild'), ['xcodebuild'] + args[1:])
    else: sys.exit('Unexpected sudo in test')
elif name == 'dscl':
    print('UserShell: ' + state.get('shell', '/bin/zsh'))
elif name == 'chsh':
    state['shell'] = args[1]; save()
elif name != 'fish':
    sys.exit('Unexpected installer test command: ' + name)
