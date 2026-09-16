"""Run with /usr/bin/python3 -m unittest discover -s tests -v.

DOTS_TEST_MISE and DOTS_TEST_FISH may point at temporary upstream binaries.
No commands target the real home directory or remote repositories.
"""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
MISE = os.environ.get("DOTS_TEST_MISE") or shutil.which("mise")
FISH = os.environ.get("DOTS_TEST_FISH") or shutil.which("fish")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dots test ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "checkout with spaces"
        shutil.copytree(SOURCE, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.home = self.base / "home"
        self.home.mkdir()
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(("GIT_", "MISE_", "XDG_")):
                del self.env[key]
        self.env.update(HOME=str(self.home), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=str(self.base / "empty.gitconfig"),
                        MISE_DATA_DIR=str(self.base / "data"),
                        MISE_CACHE_DIR=str(self.base / "cache"),
                        MISE_STATE_DIR=str(self.base / "state"),
                        MISE_CONFIG_DIR=str(self.home / ".config/mise"),
                        MISE_TRUSTED_CONFIG_PATHS=str(self.repo),
                        MISE_YES="1", MISE_COLOR="0", TERM="xterm-256color")
        paths = [str(Path(MISE).parent)] if MISE else []
        if FISH:
            paths.append(str(Path(FISH).parent))
        self.env["PATH"] = ":".join(paths + ["/usr/bin", "/bin", "/usr/sbin", "/sbin"])
        # HOME does not isolate macOS cfprefsd. Mock defaults and the mise
        # preference backend, while keeping real native dotfile operations.
        self.preferences = self.base / "preferences.json"
        self.preferences.write_text('{}')
        self.env.update(DOTS_PREFERENCES=str(self.preferences), DOTS_FIXTURE_REPO=str(self.repo),
                        DOTS_REAL_MISE=MISE or '', DOTS_XCODE_RUNNING=str(self.base / 'xcode-running'))
        commands = self.base / 'commands'
        commands.mkdir()
        stub = SOURCE / 'tests/fixtures/macos_commands.py'
        for name in ['defaults', 'pgrep'] + (['mise'] if MISE else []):
            destination = commands / name
            shutil.copy2(stub, destination)
            destination.chmod(0o755)
        self.env['PATH'] = str(commands) + ':' + self.env['PATH']
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Dots Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "fixture")

    def run_cmd(self, args, cwd=None, success=True, env=None):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.base,
                                env=env or self.env, text=True, capture_output=True, timeout=45)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, *args, **kwargs):
        return self.run_cmd(["/usr/bin/git", "-C", self.repo, *args], **kwargs)

    def dots(self, *args, **kwargs):
        return self.run_cmd([self.repo / "bin/dots", *args], **kwargs)


class GitSurface(Fixture):
    def test_allowlist(self):
        for args in [("git", "diff"), ("diff", "--staged", "extra"), ("diff", "--stat"), ("reset", "--hard"), ("git", "push"), ("diff", "--output=x"),
                     ("apply", "--force"), ("push", "--force"), ("pull", "origin"),
                     ("commit", "--amend"), ("commit", "-m", "ok", "--no-verify"),
                     ("setup", "extra"), ("help", "extra"), ("add", ".")]:
            with self.subTest(args=args):
                self.assertEqual(self.dots(*args, success=False).returncode, 2)

    def test_diff_reviews_repo_from_other_directory(self):
        config = self.repo / '.gemrc'
        config.write_text(config.read_text() + '\n# staged change\n')
        self.dots('add', '.gemrc')
        config.write_text(config.read_text() + '# unstaged change\n')
        for options in [(), ('--staged',)]:
            result = self.dots('diff', *options, cwd=self.base)
            expected = self.git('--no-pager', 'diff', '--no-ext-diff', '--no-textconv', *options, '--')
            self.assertEqual(result.stdout, expected.stdout)
            self.assertIn('+', result.stdout)
        self.assertNotIn('+# staged change', self.dots('diff').stdout)
        self.assertNotIn('unstaged change', self.dots('diff', '--staged').stdout)

    def test_literal_staging_and_staged_only_commit(self):
        name = "literal [x] $(touch PWNED).txt"
        (self.repo / name).write_text("staged\n")
        (self.repo / "unstaged.txt").write_text("not staged\n")
        self.dots("add", name)
        self.dots("diff", "--staged")
        self.dots("commit", "-m", "literal $(touch PWNED) `echo nope`")
        self.assertEqual(self.git("show", "--format=", "--name-only", "HEAD").stdout.strip(), name)
        self.assertIn("?? unstaged.txt", self.git("status", "--porcelain").stdout)
        self.assertFalse((self.repo / "PWNED").exists())

    def test_staging_boundaries_and_deletion(self):
        (self.base / "outside").write_text("outside")
        (self.repo / "escape").symlink_to(self.base, target_is_directory=True)
        for name in ["../outside", str(self.base / "outside"), "escape/outside", ".git/config", "--all", ":(glob)*"]:
            self.assertNotEqual(self.dots("add", name, success=False).returncode, 0)
        (self.repo / ".gemrc").unlink()
        self.dots("add", ".gemrc")
        self.assertIn("D  .gemrc", self.git("status", "--porcelain").stdout)

    def test_inherited_git_location_is_ignored(self):
        env = dict(self.env, GIT_DIR=str(self.base / "other.git"), GIT_WORK_TREE=str(self.base))
        self.dots("diff", env=env)

    def test_missing_upstream_and_underlying_exit_code(self):
        self.assertIn("upstream", self.dots("push", success=False).stderr)
        direct = self.git("commit", "-m", "empty", success=False)
        self.assertEqual(self.dots("commit", "-m", "empty", success=False).returncode, direct.returncode)

    def test_symlinked_executable(self):
        link = self.base / "dots"
        link.symlink_to(self.repo / "bin/dots")
        self.assertIn("Usage:", self.run_cmd([link, "help"]).stdout)
        self.run_cmd([link, "diff"])

    def test_push_pull_and_divergence(self):
        remote = self.base / "remote.git"
        self.run_cmd(["/usr/bin/git", "init", "--bare", "-b", "main", remote])
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "-u", "origin", "main")
        (self.repo / "one").write_text("one")
        self.dots("add", "one")
        self.dots("commit", "-m", "one")
        self.git("branch", "extra")
        self.git("tag", "-a", "local-only", "-m", "must stay local")
        self.git("config", "push.followTags", "true")
        self.git("config", "remote.origin.push", "refs/heads/*:refs/heads/*")
        self.dots("push")
        refs = self.run_cmd(["/usr/bin/git", "--git-dir", remote, "show-ref"]).stdout
        self.assertNotIn("extra", refs)
        self.assertNotIn("local-only", refs)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout,
                         self.run_cmd(["/usr/bin/git", "--git-dir", remote, "rev-parse", "main"]).stdout)
        peer = self.base / "peer"
        self.run_cmd(["/usr/bin/git", "clone", remote, peer])
        def peer_git(*args):
            return self.run_cmd(["/usr/bin/git", "-C", peer, *args])
        peer_git("config", "user.name", "Peer")
        peer_git("config", "user.email", "peer@example.invalid")
        (peer / "two").write_text("two")
        peer_git("add", "two"); peer_git("commit", "-m", "two"); peer_git("push")
        (self.repo / "dirty").write_text("dirty")
        self.assertIn("local changes", self.dots("pull", success=False).stderr)
        (self.repo / "dirty").unlink()
        self.dots("pull")
        self.assertTrue((self.repo / "two").exists())
        (peer / "three").write_text("three")
        peer_git("add", "three"); peer_git("commit", "-m", "three"); peer_git("push")
        (self.repo / "local").write_text("local")
        self.dots("add", "local"); self.dots("commit", "-m", "local")
        head = self.git("rev-parse", "HEAD").stdout
        self.assertNotEqual(self.dots("pull", success=False).returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.assertNotEqual(self.dots("push", success=False).returncode, 0)


class SetupStages(Fixture):
    def test_repeatable_stages_and_explicit_xcode(self):
        # Capture installation calls; never invoke package managers or sudo here.
        stubs = self.base / "stubs"
        stubs.mkdir()
        log = self.base / "calls.jsonl"
        script = '''#!/usr/bin/python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ["DOTS_CALL_LOG"], "a") as out:
    out.write(json.dumps([name] + sys.argv[1:]) + "\\n")
if name == "xcodebuild" and sys.argv[1] == "-checkFirstLaunchStatus":
    sys.exit(1)
if name == "git" and sys.argv[1] == "clone":
    target = pathlib.Path(sys.argv[-1]) / "autoload/vundle.vim"
    target.parent.mkdir(parents=True)
    target.touch()
'''
        for tool in ["brew", "mise", "git", "vim", "xcodes", "sudo", "xcodebuild"]:
            path = stubs / tool
            path.write_text(script)
            path.chmod(0o755)
        env = dict(self.env, PATH=str(stubs) + ":" + self.env["PATH"], DOTS_CALL_LOG=str(log))
        for _ in range(2):
            for stage in ["packages", "runtimes", "vim"]:
                self.run_cmd(["/bin/bash", self.repo / "scripts/setup.sh", stage], env=env)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(sum(call[0] == "git" for call in calls), 1)
        self.assertEqual(sum(call[0] == "vim" for call in calls), 2)
        for call in calls:
            if call[0] == "brew":
                self.assertEqual(call[1:4], ["bundle", "install", "--no-upgrade"])
        self.assertFalse(any(call[0] in ["sudo", "xcodes"] for call in calls))
        self.run_cmd([self.repo / "scripts/xcode.sh", "27.0"], env=env)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(calls[-5:], [["xcodes", "install", "27.0"], ["xcodes", "select", "27.0"],
                                    ["xcodebuild", "-checkFirstLaunchStatus"],
                                    ["sudo", "xcodebuild", "-runFirstLaunch"], ["xcodebuild", "-version"]])
        self.assertEqual(self.run_cmd([self.repo / "scripts/xcode.sh", "--latest"], env=env,
                                      success=False).returncode, 2)


@unittest.skipUnless(MISE, "mise binary not available")
class NativeMise(Fixture):
    def test_apply_repeat_and_unmanaged_files(self):
        fish_dir = self.home / ".config/fish"
        fish_dir.mkdir(parents=True)
        (fish_dir / "local.fish").write_text("# private\n")
        self.dots("apply", "--dry-run")
        self.assertFalse((fish_dir / "config.fish").exists())
        self.dots("apply")
        self.assertTrue((fish_dir / "config.fish").is_symlink())
        self.assertTrue((self.home / ".hammerspoon/init.lua").is_symlink())
        self.dots("apply")
        self.dots("status")
        self.assertEqual((fish_dir / "local.fish").read_text(), "# private\n")
        self.run_cmd([MISE, "-C", self.repo, "dotfiles", "status", "--missing"])
        self.run_cmd([self.home / ".local/bin/dots", "diff"])

    def test_conflicting_file_preserved(self):
        target = self.home / ".gitconfig"
        target.write_text("# existing\n")
        self.assertNotEqual(self.dots("apply", success=False).returncode, 0)
        self.assertEqual(target.read_text(), "# existing\n")
        self.assertFalse(target.is_symlink())
        self.assertFalse((self.home / ".local/bin/dots").exists())

    def test_foreign_symlink_preserved(self):
        original = self.base / "personal-config"
        original.write_text("# personal\n")
        target = self.home / ".gitconfig"
        target.symlink_to(original)
        self.assertNotEqual(self.dots("apply", success=False).returncode, 0)
        self.assertEqual(target.resolve(), original.resolve())
        self.assertEqual(original.read_text(), "# personal\n")

    def test_runtime_manifest_and_task_validation(self):
        result = self.run_cmd([MISE, "-C", self.repo / ".config/mise", "ls", "--missing", "--no-header"])
        for tool in ["ruby", "node", "python", "go", "java", "flutter"]:
            self.assertIn(tool, result.stdout)
        self.run_cmd([MISE, "-C", self.repo, "tasks", "validate"])

    def test_noninteractive_bootstrap_activation(self):
        # The installer initializes shims before running diagnostics in Bash.
        self.run_cmd(['/bin/bash', '-c',
                      'activation=$(mise activate bash --shims); eval "$activation"; mise doctor'],
                     cwd=self.home)

    def test_doctor_does_not_install_missing_runtimes(self):
        self.dots("apply")
        result = self.dots("doctor", success=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stdout + result.stderr)
        self.assertFalse((self.base / "data/installs").exists())

    @unittest.skipUnless(FISH, "fish binary not available")
    def test_fish_syntax_and_silent_startup(self):
        self.dots("apply")
        config = self.repo / ".config/fish/config.fish"
        self.run_cmd([FISH, "--no-config", "-n", config])
        result = self.run_cmd([FISH, "-c", "true"])
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    @unittest.skipUnless(FISH, "fish binary not available")
    def test_fish_activation_and_project_override(self):
        # Tiny executable fixtures test selection without installing real runtimes.
        (self.repo / ".config/mise/config.toml").write_text('[tools]\nnode = "24.21.0"\n')
        for version in ["24.21.0", "22.22.0"]:
            executable = self.base / "data/installs/node" / version / "bin/node"
            executable.parent.mkdir(parents=True)
            executable.write_text('#!/bin/sh\nprintf "v' + version + '\\n"\n')
            executable.chmod(0o755)
        project = self.repo / "example-project"
        project.mkdir()
        (project / "mise.toml").write_text('[tools]\nnode = "22.22.0"\n')
        self.dots("apply")
        code = ('mise hook-env --force --shell fish | source; node --version; '
                'cd "$argv[1]"; mise hook-env --force --shell fish | source; node --version')
        result = self.run_cmd([FISH, "-i", "-c", code, project], cwd=self.home)
        self.assertEqual(result.stdout.splitlines(), ["v24.21.0", "v22.22.0"])


if __name__ == "__main__":
    unittest.main()
