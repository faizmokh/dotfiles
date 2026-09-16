import json
import errno
import os
import pty
import re
import select
import signal
import time
from pathlib import Path
import shutil
from test_dots import Fixture, SOURCE


class Installer(Fixture):
    def setUp(self):
        super().setUp()
        self.bin = self.base / 'installer-bin'; self.bin.mkdir()
        for name in ['uname','xcode-select','sleep','curl','brew-template','git','mise','xcodes','xcodebuild','sudo','dscl','chsh']:
            target = self.bin / name
            shutil.copy2(SOURCE / 'tests/fixtures/installer_commands.py', target); target.chmod(0o755)
        prefix = self.base / 'brew/bin'; prefix.mkdir(parents=True)
        (prefix / 'fish').write_text('#!/bin/sh\nexit 0\n'); (prefix / 'fish').chmod(0o755)
        (self.base / 'shells').write_text('/bin/zsh\n')
        self.state = self.base / 'installer-state.json'
        self.state.write_text('{}')
        self.env.update(INSTALL_TEST_BASE=str(self.base), INSTALL_TEST_SOURCE=str(self.repo),
                        PATH=str(self.bin) + ':' + self.env['PATH'])
        # Redirect fixed macOS paths in the temporary checkout only.
        path = self.repo / 'install.sh'
        path.write_text(path.read_text().replace('/opt/homebrew', str(self.base / 'brew')))
        # Prefix has spaces, so quote the two formerly constant executable paths.
        content = path.read_text().replace('if [ ! -x ' + str(self.base / 'brew/bin/brew') + ' ];',
                                          'if [ ! -x "' + str(self.base / 'brew/bin/brew') + '" ];')
        content = content.replace('$(' + str(self.base / 'brew/bin/brew') + ' shellenv bash)',
                                  '$("' + str(self.base / 'brew/bin/brew') + '" shellenv bash)')
        path.write_text(content)
        path = self.repo / 'scripts/setup.sh'
        path.write_text(path.read_text().replace('/etc/shells', '"' + str(self.base / 'shells') + '"'))
        self.git('remote','add','origin','https://github.com/faizmokh/dotfiles.git')
        self.git('add','install.sh','scripts/setup.sh');self.git('commit','-m','Isolated installer fixture')

    def calls(self):
        return [json.loads(line) for line in (self.base / 'installer-log.jsonl').read_text().splitlines()]

    def install(self, remote=False, **kwargs):
        args = ['/bin/bash', '-c', (self.repo / 'install.sh').read_text()] if remote else ['/bin/bash', self.repo / 'install.sh']
        return self.run_cmd(args, **kwargs)

    def test_fresh_remote_command_and_repeat(self):
        result = self.install(remote=True)
        stages = re.findall(r'^RUN\s+\[(\d+)/15\] (.+)$', result.stdout, re.M)
        self.assertEqual([int(number) for number, _ in stages], list(range(1, 16)))
        self.assertEqual([label for _, label in stages], ['Platform', 'Command Line Tools',
            'Homebrew', 'Prerequisites', 'Checkout', 'Trust', 'Dotfile conflicts', 'Packages', 'Runtimes',
            'Pi', 'Vim', 'Xcode', 'Dotfiles', 'Login shell', 'Diagnostics'])
        self.assertEqual(len(re.findall(r'^DONE\s+\[\d+/15\].+\(\d+s\)$', result.stdout, re.M)), 15)
        self.assertIn('Setup complete: 15/15 stages', result.stdout)
        self.assertNotIn('\x1b', result.stdout + result.stderr)
        calls = self.calls()
        self.assertLess(calls.index(['mise', 'activate', 'bash', '--shims']),
                        calls.index(['stage', 'setup:packages']))
        self.assertIn(['xcode-select','--install'],calls)
        self.assertIn(['xcodes','install','--latest','--select'], calls)
        stages=[call[1] for call in calls if call[0]=='stage']
        self.assertEqual(stages,['setup:packages','setup:runtimes','setup:pi','setup:vim','setup:xcode','setup:dotfiles','setup:shell','doctor'])
        checkout = self.home / 'Developer/dotfiles'
        trusts = [call[2] for call in calls if call[:2]==['mise','trust']]
        self.assertEqual(trusts,[str(checkout/'mise.toml'),str(checkout/'.config/mise/config.toml')])
        conflict_check = ['mise', '-C', str(checkout.resolve()), 'dotfiles', 'status', '--json']
        self.assertLess(calls.index(['mise', 'trust', trusts[-1]]), calls.index(conflict_check))
        self.assertLess(calls.index(conflict_check), calls.index(['stage', 'setup:packages']))
        self.assertEqual(json.loads(self.state.read_text())['shell'],str(self.base/'brew/bin/fish'))
        (checkout/'local-change').write_text('keep')
        count=len(calls); repeated = self.install(remote=True)
        for message in ['Reusing installed Command Line Tools', 'Reusing installed Homebrew',
                        'Verifying existing checkout', 'Reusing the selected Xcode']:
            self.assertIn(message, repeated.stdout)
        later=self.calls()[count:]
        self.assertFalse(any(call[0] in ['curl','xcodes','chsh'] for call in later))
        self.assertFalse(any(call[:2]==['git','clone'] for call in later))
        self.assertEqual((checkout/'local-change').read_text(),'keep')

    def test_auth_failure_stops_before_application(self):
        self.env['INSTALL_TEST_AUTH_FAIL']='1'
        result=self.install(success=False)
        self.assertEqual(result.returncode,42)
        self.assertIn('rerun',result.stderr)
        self.assertRegex(result.stderr, r'FAILED\s+\[12/15\] Xcode failed after \d+s \(exit 42\)')
        self.assertIn('Complete Apple authentication', result.stderr)
        self.assertNotIn('Setup complete', result.stdout)
        self.assertNotIn(['stage','setup:dotfiles'],self.calls())
        self.assertNotIn(['stage','setup:shell'],self.calls())

    def test_interrupted_clt_is_resumable(self):
        self.env['INSTALL_TEST_INTERRUPT']='1'
        result = self.install(success=False)
        self.assertEqual(result.returncode,130)
        self.assertIn('Command Line Tools interrupted', result.stderr)
        self.assertNotIn('Setup complete', result.stdout)
        self.assertFalse(any(call[0]=='curl' for call in self.calls()))
        del self.env['INSTALL_TEST_INTERRUPT']
        self.install()

    def test_wrong_checkout_origin_is_not_changed(self):
        self.git('remote','set-url','origin','https://example.invalid/other.git')
        result=self.install(success=False)
        self.assertIn('Unexpected checkout origin',result.stderr)
        self.assertFalse(any(call[:2]==['mise','trust'] for call in self.calls()))
        self.assertEqual(self.git('config','remote.origin.url').stdout.strip(),'https://example.invalid/other.git')

    def test_dots_setup_uses_same_installer(self):
        self.dots('setup')
        self.assertIn(['stage','setup:shell'],self.calls())
        self.assertIn(['stage','doctor'],self.calls())

    def test_conflicting_directory_is_preserved(self):
        checkout = self.home / 'Developer/dotfiles'
        checkout.mkdir(parents=True)
        (checkout / 'personal').write_text('keep')
        self.assertNotEqual(self.install(remote=True, success=False).returncode, 0)
        self.assertEqual((checkout / 'personal').read_text(), 'keep')
        self.assertFalse(any(call[:2] == ['mise', 'trust'] for call in self.calls()))

    def test_core_stage_failure_stops_sequence(self):
        self.env['INSTALL_TEST_FAIL_STAGE'] = 'setup:runtimes'
        self.assertEqual(self.install(success=False).returncode, 42)
        self.assertNotIn(['stage', 'setup:pi'], self.calls())

    def test_dotfile_conflicts_stop_before_setup_tasks(self):
        for remote in (False, True):
            with self.subTest(remote=remote):
                target = self.home / '.gitconfig'
                target.write_text('# personal config\n')
                result = self.install(remote=remote, success=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn('[7/15] Dotfile conflicts failed', result.stderr)
                self.assertIn(str(target), result.stderr)
                self.assertEqual(target.read_text(), '# personal config\n')
                self.assertFalse(any(call[0] == 'stage' for call in self.calls()))
                self.assertFalse((self.home / '.local/state/dots').exists())
                self.assertFalse((self.home / '.config/fish/config.fish').exists())
                target.unlink()

    def test_foreign_symlink_conflict_is_preserved(self):
        original = self.home / 'personal.gitconfig'
        original.write_text('# personal config\n')
        target = self.home / '.gitconfig'
        target.symlink_to(original)
        result = self.install(success=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(target), result.stderr)
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), original.resolve())
        self.assertEqual(original.read_text(), '# personal config\n')
        self.assertFalse(any(call[0] == 'stage' for call in self.calls()))

    def test_android_onboarding_does_not_fail_foundation(self):
        commands = self.base / 'doctor-commands'; commands.mkdir()
        for name in ['brew', 'fish', 'mise', 'git', 'git-lfs', 'xcodes', 'wezterm',
                     'lazygit', 'opencode', 'xcodebuild', 'python-check']:
            command = commands / name
            command.write_text('#!/bin/sh\nexit 0\n'); command.chmod(0o755)
        vundle = self.home / '.vim/bundle/Vundle.vim/autoload/vundle.vim'
        vundle.parent.mkdir(parents=True); vundle.touch()
        script = self.repo / 'scripts/doctor.sh'
        script.write_text(script.read_text().replace('/usr/bin/python3', 'python-check'))
        self.env['PATH'] = str(commands) + ':' + self.env['PATH']
        result = self.run_cmd(['/bin/bash', script])
        self.assertIn('NEXT   Review Android licenses', result.stdout)
        self.assertNotIn('FAILED', result.stdout + result.stderr)
        (commands / 'xcodebuild').write_text('#!/bin/sh\nexit 9\n')
        self.assertNotEqual(self.run_cmd(['/bin/bash', script], success=False).returncode, 0)

    def terminal_install(self):
        child, terminal = pty.fork()
        if child == 0:
            os.execve('/bin/bash', ['/bin/bash', str(self.repo / 'install.sh')], self.env)
        output = b''
        answered = False
        deadline = time.monotonic() + 30
        try:
            while time.monotonic() < deadline:
                if not select.select([terminal], [], [], 0.1)[0]:
                    continue
                try:
                    data = os.read(terminal, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                output += data
                if b'Fixture authentication prompt:' in output and not answered:
                    os.write(terminal, b'continue\n')
                    answered = True
            else:
                self.fail('Installer terminal timed out: ' + output.decode(errors='replace'))
            _, status = os.waitpid(child, 0)
            child = None
            self.assertEqual(status, 0, output.decode(errors='replace'))
            return output.decode()
        finally:
            os.close(terminal)
            if child is not None:
                os.kill(child, signal.SIGKILL)
                os.waitpid(child, 0)

    def test_terminal_color_and_interactive_prompt(self):
        self.env.pop('NO_COLOR', None)
        self.env['TERM'] = 'xterm-256color'
        self.env['INSTALL_TEST_PROMPT'] = 'setup:xcode'
        output = self.terminal_install()
        self.assertIn('\x1b[36mRUN', output)
        self.assertIn('Fixture authentication accepted', output)
        self.assertIn('Setup complete: 15/15', output)

    def test_terminal_without_color(self):
        for term, no_color in [('xterm-256color', ''), ('dumb', None)]:
            with self.subTest(term=term):
                self.env['TERM'] = term
                if no_color is None:
                    self.env.pop('NO_COLOR', None)
                else:
                    self.env['NO_COLOR'] = no_color
                self.assertNotIn('\x1b', self.terminal_install())

    def test_clt_wait_updates_and_timeout(self):
        self.env['INSTALL_TEST_CLT_WAITS'] = '121'
        result = self.install(success=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Waiting for Command Line Tools (30s)', result.stdout)
        self.assertIn('Waiting for Command Line Tools (1200s)', result.stdout)
        self.assertIn('after 20 minutes', result.stderr)
        self.assertIn('[2/15] Command Line Tools failed', result.stderr)
        self.assertNotIn('Setup complete', result.stdout)
        self.assertFalse(any(call[0] == 'curl' for call in self.calls()))

    def test_installer_messages_are_ascii(self):
        # Keep authored output free of emoji and terminal-dependent glyphs.
        (SOURCE / 'install.sh').read_text().encode('ascii')

    def test_signal_reports_interruption(self):
        self.env['INSTALL_TEST_SIGNAL'] = '1'
        result = self.install(success=False)
        self.assertEqual(result.returncode, 130)
        self.assertIn('[2/15] Command Line Tools interrupted', result.stderr)
        self.assertIn('1/15 stages completed', result.stderr)
        self.assertNotIn('Setup complete', result.stdout)

    def test_dotfile_failure_offers_conflict_recovery(self):
        self.env['INSTALL_TEST_FAIL_STAGE'] = 'setup:dotfiles'
        result = self.install(success=False)
        self.assertEqual(result.returncode, 42)
        self.assertIn('[13/15] Dotfiles failed', result.stderr)
        self.assertIn('back up and move any reported conflicting files', result.stderr)
        self.assertNotIn(['stage', 'setup:shell'], self.calls())
        self.assertNotIn('Setup complete', result.stdout)
