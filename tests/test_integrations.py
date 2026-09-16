import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import unittest

from test_dots import Fixture, MISE, SOURCE


@unittest.skipUnless(MISE, 'mise binary not available')
class PiIntegration(Fixture):
    def seed_remote(self):
        seed = self.base / 'pi seed'
        remote = self.base / 'piconf.git'
        self.run_cmd(['/usr/bin/git', 'init', '-b', 'main', seed])
        def git(*args):
            return self.run_cmd(['/usr/bin/git', '-C', seed, *args])
        git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid')
        (seed / 'agent').mkdir()
        (seed / 'agent/settings.json').write_text('{"theme":"dark"}\n')
        (seed / '.gitignore').write_text('agent/auth.json\nagent/sessions/\n')
        git('add', '.'); git('commit', '-m', 'Pi fixture')
        self.run_cmd(['/usr/bin/git', 'clone', '--bare', seed, remote])
        self.run_cmd(['/usr/bin/git', 'config', '--file', self.env['GIT_CONFIG_GLOBAL'],
                      'url.' + remote.as_uri() + '.insteadOf', 'https://github.com/faizmokh/piconf.git'])
        return seed, remote

    def setup_pi(self, **kwargs):
        return self.run_cmd(['/usr/bin/python3', self.repo / 'scripts/piconf.py', 'setup'], **kwargs)

    def test_missing_clone_then_preserve_dirty_checkout(self):
        self.seed_remote()
        self.setup_pi()
        pi = self.home / '.pi'
        original_head = self.run_cmd(['/usr/bin/git', '-C', pi, 'rev-parse', 'HEAD']).stdout
        settings = pi / 'agent/settings.json'
        settings.write_text('{"theme":"light"}\n')
        (pi / 'agent/auth.json').write_text('{"secret":"private"}')
        self.setup_pi()
        self.assertEqual(settings.read_text(), '{"theme":"light"}\n')
        self.assertEqual(self.run_cmd(['/usr/bin/git', '-C', pi, 'rev-parse', 'HEAD']).stdout, original_head)
        self.assertIn('agent/settings.json', self.dots('pi', 'status').stdout)
        self.assertNotIn('auth.json', self.dots('pi', 'status').stdout)
        self.assertIn('local changes', self.dots('pi', 'pull', success=False).stderr)
        self.assertNotEqual(self.dots('pi', 'add', 'agent/auth.json', success=False).returncode, 0)
        self.assertNotEqual(self.dots('pi', 'add', '../outside', success=False).returncode, 0)

    def test_verified_pi_git_surface_and_remote(self):
        seed, remote = self.seed_remote()
        self.setup_pi()
        pi = self.home / '.pi'
        for key, value in [('user.name','Test'), ('user.email','test@example.invalid')]:
            self.run_cmd(['/usr/bin/git', '-C', pi, 'config', key, value])
        (pi / 'agent/settings.json').write_text('{"theme":"light"}\n')
        self.dots('pi', 'add', 'agent/settings.json')
        self.assertIn('light', self.dots('pi', 'diff', '--staged').stdout)
        self.dots('pi', 'commit', '-m', 'Pi update')
        self.dots('pi', 'push')
        self.assertEqual(self.run_cmd(['/usr/bin/git', '-C', pi, 'rev-parse', 'HEAD']).stdout,
                         self.run_cmd(['/usr/bin/git', '--git-dir', remote, 'rev-parse', 'main']).stdout)
        self.dots('pi', 'pull')
        self.assertEqual(self.dots('pi', 'push', '--force', success=False).returncode, 2)
        self.assertEqual(self.dots('pi', 'git', 'reset', success=False).returncode, 2)
        self.assertEqual(self.git('status', '--porcelain').stdout, '')
        self.run_cmd(['/usr/bin/git', '-C', pi, 'remote', 'set-url', 'origin', 'https://example.invalid/other.git'])
        self.assertIn('unexpected origin', self.setup_pi(success=False).stderr)
        self.assertIn('unexpected origin', self.dots('pi', 'status', success=False).stderr)

    def test_conflicting_directory_is_preserved(self):
        pi = self.home / '.pi'
        pi.mkdir(); (pi / 'personal.txt').write_text('keep me')
        self.assertNotEqual(self.setup_pi(success=False).returncode, 0)
        self.assertEqual((pi / 'personal.txt').read_text(), 'keep me')
        self.assertFalse((pi / '.git').exists())


@unittest.skipUnless(MISE, 'mise binary not available')
class XcodeIntegration(Fixture):
    def read_desired(self):
        spec = importlib.util.spec_from_file_location('xcode', self.repo / 'scripts/xcode-settings.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module.desired()

    def test_three_mappings_and_owned_legacy_cleanup(self):
        root = self.home / 'Library/Developer/Xcode/UserData'
        pairs = [
            ('themes/latte.xccolortheme', 'FontAndColorThemes/Catppuccin Latte.xccolortheme'),
            ('themes/dracula.xccolortheme', 'FontAndColorThemes/Dracula Maple.xccolortheme'),
            ('keybindings.idekeybindings', 'KeyBindings/Default.idekeybindings'),
        ]
        obsolete = root / 'FontAndColorThemes/Mocha.xccolortheme'
        for _, relative in pairs + [('', 'FontAndColorThemes/Mocha.xccolortheme')]:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(self.repo / 'xcode' / relative)
        personal = root / 'FontAndColorThemes/Spartan.xccolortheme'
        personal.write_text('personal theme')
        foreign = root / 'FontAndColorThemes/Dracula.xccolortheme'
        foreign.symlink_to(self.base / 'other checkout/theme')
        self.dots('apply', '--dry-run')
        self.assertTrue(obsolete.is_symlink())
        # Any unrelated conflict prevents cleanup too.
        conflict = self.home / '.vimrc'; conflict.write_text('keep')
        self.assertNotEqual(self.dots('apply', success=False).returncode, 0)
        self.assertTrue(obsolete.is_symlink())
        conflict.unlink()
        self.dots('apply')
        self.assertFalse(obsolete.is_symlink())
        self.assertEqual(personal.read_text(), 'personal theme')
        self.assertTrue(foreign.is_symlink())
        for source, relative in pairs:
            self.assertEqual((root / relative).resolve(), (self.repo / 'xcode' / source).resolve())
        files = [p for p in (self.repo / 'xcode').rglob('*') if p.is_file()]
        self.assertEqual(len(files), 3)
        before = {p: p.read_bytes() for p in files}
        self.dots('capture', 'xcode')
        self.assertEqual(before, {p: p.read_bytes() for p in files})
        self.dots('apply')

    def test_dry_run_backups_types_and_rollback(self):
        original = {'DVTTextShowMinimap': True, 'DVTDeveloperAccountManagerAppleIDLists': ['private'],
                    'Unrelated': 123, 'DVTTextAutoHighlightTokensDelay': 0.75}
        self.preferences.write_text(json.dumps(original))
        self.dots('apply', '--dry-run')
        backup_dir = self.home / '.local/state/dots/xcode'
        self.assertFalse(backup_dir.exists())
        self.assertEqual(json.loads(self.preferences.read_text()), original)
        self.dots('apply')
        desired = self.read_desired()
        live = json.loads(self.preferences.read_text())
        for key, value in desired.items():
            self.assertEqual(live[key], value)
            self.assertIs(type(live[key]), type(value))
        self.assertEqual(live['Unrelated'], 123)
        backups = list(backup_dir.glob('*.json'))
        self.assertEqual(len(backups), 1)
        backup = backups[0]
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('private', backup.read_text())
        self.dots('apply')
        self.assertEqual(len(list(backup_dir.glob('*.json'))), 1)
        self.dots('restore', 'xcode', str(backup))
        self.assertEqual(json.loads(self.preferences.read_text()), original)

    def test_running_xcode_stops_before_any_mutation(self):
        Path(self.env['DOTS_XCODE_RUNNING']).touch()
        for args in [('apply',), ('capture', 'xcode')]:
            self.assertIn('Quit Xcode', self.dots(*args, success=False).stderr)
        self.assertFalse((self.home / '.local/bin/dots').exists())
        self.assertFalse((self.home / '.local/state/dots').exists())
        self.dots('apply', '--dry-run')

    def test_capture_only_allowlisted_files_and_keys_without_staging(self):
        self.dots('apply')
        live = json.loads(self.preferences.read_text())
        live['DVTTextShowMinimap'] = True
        live['AccountSecret'] = 'never-capture'
        self.preferences.write_text(json.dumps(live))
        root = self.home / 'Library/Developer/Xcode/UserData'
        path = root / 'FontAndColorThemes/Dracula Maple.xccolortheme'
        data = plistlib.loads(path.read_bytes())
        data['TestCaptureMarker'] = 'changed'
        # Model Xcode replacing a symlink with a regular file on save.
        path.unlink(); path.write_bytes(plistlib.dumps(data))
        (root / 'Provisioning Profiles').mkdir()
        (root / 'Provisioning Profiles/private.mobileprovision').write_text('private profile')
        self.dots('capture', 'xcode')
        self.assertTrue(self.read_desired()['DVTTextShowMinimap'])
        stored = plistlib.loads((self.repo / 'xcode/themes/dracula.xccolortheme').read_bytes())
        self.assertEqual(stored['TestCaptureMarker'], 'changed')
        self.assertNotIn('never-capture', (self.repo / 'mise.toml').read_text())
        self.assertFalse((self.repo / 'xcode/Provisioning Profiles').exists())
        self.assertEqual(self.git('diff', '--cached', '--name-only').stdout, '')
        self.assertNotEqual(self.dots('apply', success=False).returncode, 0)

    def test_capture_invalid_type_is_atomic(self):
        self.dots('apply')
        before = (self.repo / 'mise.toml').read_bytes()
        live = json.loads(self.preferences.read_text()); live['DVTTextShowMinimap'] = 'false'
        self.preferences.write_text(json.dumps(live))
        self.assertNotEqual(self.dots('capture', 'xcode', success=False).returncode, 0)
        self.assertEqual((self.repo / 'mise.toml').read_bytes(), before)

    def test_restore_rejects_unapproved_keys(self):
        backup = self.base / 'bad.json'
        backup.write_text(json.dumps({'schema':1, 'domain':'com.apple.dt.Xcode',
            'preferences':{'PrivateKey':{'present':True,'value':'no'}}}))
        self.assertNotEqual(self.dots('restore', 'xcode', str(backup), success=False).returncode, 0)
        self.assertEqual(self.preferences.read_text(), '{}')


WEZTERM = os.environ.get('DOTS_TEST_WEZTERM') or shutil.which('wezterm')


@unittest.skipUnless(WEZTERM, 'wezterm binary not available')
class WezTermIntegration(Fixture):
    def test_real_config_loads(self):
        result = self.run_cmd([WEZTERM, '--config-file', self.repo / '.config/wezterm/wezterm.lua',
                               'show-keys', '--lua'])
        self.assertIn('pi-and-lazygit', result.stdout)

    def test_callbacks_spawn_fish_without_typing_into_active_pane(self):
        script = r'''
local actual = require 'wezterm'
local events, spawned, split = {}, nil, nil
local is_git = true
local action = setmetatable({}, {__index = function(_, key)
    if key == 'ToggleFullScreen' then return key end
    return function(value) return value end
end})
package.loaded.wezterm = {
    home_dir = '/home/test', hostname = function() return 'local-mac' end,
    on = function(name, callback) events[name] = callback end,
    action = action, font_with_fallback = function(value) return value end,
    run_child_process = function(args)
        assert(args[1] == '/usr/bin/git')
        assert(args[2] == '-C')
        return is_git, is_git and 'true\n' or ''
    end,
}
local config = dofile(SOURCE_PATH)
assert(config.default_prog[1] == '/opt/homebrew/bin/fish')
assert(config.default_prog[2] == '-l')
assert(config.set_environment_variables == nil)
local new_pane = { split = function(_, args) split = args end }
local mux = { spawn_tab = function(_, args) spawned = args; return {}, new_pane end }
local window = { mux_window = function() return mux end }
local pane = { get_current_working_dir = function()
    return {file_path = '/work/a folder $(touch nope)', host = 'local-mac'}
end }
for _, pair in ipairs({{'pi-and-lazygit','pi'}, {'opencode-and-lazygit','opencode'}, {'lazygit','lazygit'}}) do
    spawned, split = nil, nil
    events[pair[1]](window, pane)
    assert(spawned.args[1] == '/opt/homebrew/bin/fish')
    assert(spawned.args[2] == '-lic')
    assert(spawned.args[3] == pair[2])
    assert(spawned.cwd == '/work/a folder $(touch nope)')
    if pair[2] ~= 'lazygit' then
        assert(split.args[3] == 'lazygit' and split.size == 0.5)
        assert(split.cwd == spawned.cwd)
    else assert(split == nil) end
end
is_git, split = false, nil
events['pi-and-lazygit'](window, pane)
assert(split == nil)
pane.get_current_working_dir = function() return {file_path='/remote', host='remote-host'} end
events['pi-and-lazygit'](window, pane)
assert(spawned.cwd == '/home/test')
package.loaded.wezterm = actual
return {}
'''
        script = script.replace('SOURCE_PATH', json.dumps(str(self.repo / '.config/wezterm/wezterm.lua')))
        path = self.base / 'wezterm-test.lua'
        path.write_text(script)
        self.run_cmd([WEZTERM, '--config-file', path, 'show-keys', '--lua'])
