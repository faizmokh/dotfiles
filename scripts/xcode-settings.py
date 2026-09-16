#!/usr/bin/python3
"""Capture and back up only portable Xcode settings; mise applies defaults."""
import datetime
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
DOMAIN = 'com.apple.dt.Xcode'
BEGIN = '# BEGIN XCODE PREFERENCES (dots capture xcode updates only this block)'
END = '# END XCODE PREFERENCES'
TYPES = {
    'XCFontAndColorCurrentTheme': str,
    'XCFontAndColorCurrentDarkTheme': str,
    'IDEKeyBindingCurrentPreferenceSet': str,
    'DVTTextEnablePredictiveCompletion': bool,
    'DVTTextAutoHighlightTokensDelay': float,
    'DVTTextShowAuthors': bool,
    'DVTTextShowCodeCoverage': bool,
    'DVTTextShowFoldingSidebar': bool,
    'DVTTextShowMinimap': bool,
    'IDEAlwaysShowEditorTabBar': bool,
    'IDEFileExtensionDisplayMode': int,
}


def validate(key, value):
    # bool is an int subclass: exact types matter to macOS defaults.
    expected = TYPES[key]
    if type(value) is not expected:
        raise ValueError('Unexpected type for ' + key + '; expected ' + expected.__name__)
    return value


def desired():
    text = (REPO / 'mise.toml').read_text()
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Xcode preference block markers must occur exactly once.')
    block = text.split(BEGIN, 1)[1].split(END, 1)[0].strip().splitlines()
    if block[0] != '[bootstrap.macos.defaults."' + DOMAIN + '"]':
        raise ValueError('Unexpected Xcode preference domain.')
    values = {}
    for line in block[1:]:
        key, raw = line.split(' = ', 1)
        if key not in TYPES or key in values:
            raise ValueError('Unexpected/duplicate Xcode preference: ' + key)
        values[key] = validate(key, json.loads(raw))
    if set(values) != set(TYPES):
        raise ValueError('Incomplete Xcode preference allowlist.')
    return values


def live():
    # defaults talks to cfprefsd; never copy/import the whole preferences plist.
    result = subprocess.run(['defaults', 'export', DOMAIN, '-'], capture_output=True)
    if result.returncode:
        # A fresh Mac legitimately has no Xcode domain yet. Other failures stop.
        domains = subprocess.run(['defaults', 'domains'], capture_output=True, text=True, check=True)
        if DOMAIN not in [item.strip() for item in domains.stdout.strip().split(',')]:
            return {}
        raise ValueError('Could not read Xcode preferences: ' + result.stderr.decode(errors='replace'))
    all_values = plistlib.loads(result.stdout)
    return {key: all_values[key] for key in TYPES if key in all_values}


def closed():
    result = subprocess.run(['pgrep', '-x', 'Xcode'], stdout=subprocess.DEVNULL)
    if result.returncode == 0:
        raise ValueError('Quit Xcode before applying or capturing its settings; dots never quits it for you.')
    if result.returncode != 1:
        raise ValueError('Could not determine whether Xcode is running.')


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            if path.exists():
                os.chmod(temp, path.stat().st_mode & 0o777)
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()


def backup(wanted, current):
    changes = {key: {'present': key in current, 'value': current.get(key)}
               for key in wanted if key not in current or type(current[key]) is not type(wanted[key])
               or current[key] != wanted[key]}
    if not changes:
        print('Xcode preferences already match; no backup needed.')
        return
    state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state')))
    folder = state / 'dots/xcode'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    destination = folder / (stamp + '.json')
    payload = {'schema': 1, 'domain': DOMAIN, 'preferences': changes}
    with open(destination, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')
    print('Xcode preference backup: ' + str(destination))


def capture(wanted, current):
    from xcode_files import mappings
    writes = []
    # Validate every input before changing repository files.
    for source, target in mappings():
        data = target.read_bytes()
        plistlib.loads(data)
        writes.append((source, data))
    missing = []
    for key in wanted:
        if key in current:
            wanted[key] = validate(key, current[key])
        else:
            missing.append(key)
    # Missing keys may represent implicit app defaults. Retain the explicit pin.
    if missing:
        print('Keeping stored values for absent keys: ' + ', '.join(missing))
    block = BEGIN + '\n[bootstrap.macos.defaults."' + DOMAIN + '"]\n'
    block += ''.join(key + ' = ' + json.dumps(value, ensure_ascii=True) + '\n' for key, value in wanted.items())
    text = (REPO / 'mise.toml').read_text()
    text = text.split(BEGIN, 1)[0] + block + END + text.split(END, 1)[1]
    writes.append((REPO / 'mise.toml', text.encode()))
    for path, data in writes:
        if path.read_bytes() != data:
            atomic_write(path, data)
    print('Captured declared Xcode settings. Review dots git diff; nothing was staged.')


def restore(path):
    closed()
    payload = json.loads(Path(path).read_text())
    if payload.get('schema') != 1 or payload.get('domain') != DOMAIN:
        raise ValueError('Not a dots Xcode preference backup.')
    entries = payload['preferences']
    if not isinstance(entries, dict) or not entries or not set(entries) <= set(TYPES):
        raise ValueError('Backup contains unapproved preference keys.')
    for key, entry in entries.items():
        if type(entry.get('present')) is not bool:
            raise ValueError('Invalid backup presence flag.')
        if entry['present']:
            validate(key, entry['value'])
    current = live()
    # Preserve current values before rollback, including absent keys.
    folder = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'dots/xcode'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', prefix='before-restore-', suffix='.json', dir=folder, delete=False) as handle:
        json.dump({'schema': 1, 'domain': DOMAIN, 'preferences': {
            key: {'present': key in current, 'value': current.get(key)} for key in entries}}, handle, indent=2)
        print('Before-restore backup: ' + handle.name)
    flags = {str: '-string', bool: '-bool', int: '-int', float: '-float'}
    for key, entry in entries.items():
        if entry['present']:
            value = entry['value']
            text = ('true' if value else 'false') if type(value) is bool else str(value)
            subprocess.run(['defaults', 'write', DOMAIN, key, flags[type(value)], text], check=True)
        elif key in current:
            subprocess.run(['defaults', 'delete', DOMAIN, key], check=True)
    print('Restored selected preferences. A later dots apply will restore the repository values.')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'restore':
        restore(sys.argv[2])
        return
    if len(sys.argv) != 2 or sys.argv[1] not in ('preflight', 'backup', 'status', 'check', 'capture'):
        raise ValueError('Usage: xcode-settings.py preflight|backup|status|check|capture')
    action = sys.argv[1]
    wanted = desired()
    if action in ('preflight', 'backup', 'capture'):
        closed()
    if action == 'preflight':
        return
    current = live()
    if action == 'backup':
        backup(wanted, current)
    elif action == 'capture':
        capture(wanted, current)
    else:
        drift = False
        for key, value in wanted.items():
            matches = key in current and type(current[key]) is type(value) and current[key] == value
            if not matches:
                drift = True
                print('Xcode ' + key + ': ' + repr(current.get(key, '<unset>')) + ' -> ' + repr(value))
        if not drift:
            print('Xcode preferences match.')
        if action == 'check' and drift:
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, plistlib.InvalidFileException) as error:
        sys.exit('dots: ' + str(error))
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
