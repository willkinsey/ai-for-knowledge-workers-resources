#!/usr/bin/env python3
"""Isolated installer tests; all fixture targets are created under /private/tmp."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = SCRIPT_DIR.parent


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="luna-worker-setup-test-", dir="/private/tmp")
        cls.root = Path(cls.temp.name)
        cls.package = cls.root / "package-fixture"
        shutil.copytree(
            PACKAGE_DIR / "scripts",
            cls.package / "scripts",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(PACKAGE_DIR / "templates", cls.package / "templates")
        shutil.copytree(PACKAGE_DIR / "skills" / "delegate-bounded-work", cls.package / "skills" / "delegate-bounded-work")
        cls.installer = cls.package / "scripts" / "install.py"
        cls.verifier = cls.package / "scripts" / "verify.py"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def command(self, script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_dry_run_makes_no_target_writes(self) -> None:
        target = self.root / "dry-run-user"
        target.mkdir()
        (target / "config.toml").write_text('unrelated = "retain"\n', encoding="utf-8")
        before = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}

        result = self.command(self.installer, "--target", str(target))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mode: dry-run", result.stdout)
        after = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file()}
        self.assertEqual(after, before)
        self.assertEqual(list(target.rglob("*.bak-*")), [])

    def test_user_default_target_uses_codex_home_or_isolated_home(self) -> None:
        codex_home = self.root / "env-codex-home"
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        result = self.command(self.installer, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Target root: {codex_home}", result.stdout)
        self.assertFalse(codex_home.exists())

        isolated_home = self.root / "isolated-home"
        isolated_home.mkdir()
        env.pop("CODEX_HOME", None)
        env["HOME"] = str(isolated_home)
        fallback = self.command(self.installer, env=env)
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertIn(f"Target root: {isolated_home / '.codex'}", fallback.stdout)
        self.assertFalse((isolated_home / ".codex").exists())

    def test_apply_preserves_unrelated_content_backs_up_changes_and_is_idempotent(self) -> None:
        target = self.root / "apply-user"
        (target / "agents").mkdir(parents=True)
        (target / "skills" / "delegate-bounded-work").mkdir(parents=True)
        original = {
            "config.toml": (
                'custom_root = "retain me"\n\n'
                '[agents]\n'
                'extra_setting = "keep"\n'
                'enabled = false # keep this comment\n\n'
                '[other]\n'
                'value = "also keep"\n'
            ).encode(),
            "agents/luna-worker.toml": b'name = "old role"\n',
            "AGENTS.md": b"# Existing project instructions\nKeep this paragraph.\n",
            "skills/delegate-bounded-work/SKILL.md": b"old skill\n",
        }
        for relative, contents in original.items():
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

        first = self.command(self.installer, "--target", str(target), "--apply")

        self.assertEqual(first.returncode, 0, first.stderr)
        config_bytes = (target / "config.toml").read_bytes()
        config = tomllib.loads(config_bytes.decode())
        self.assertEqual(config["custom_root"], "retain me")
        self.assertEqual(config["agents"]["extra_setting"], "keep")
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 3)
        self.assertEqual(config["other"]["value"], "also keep")
        self.assertIn("# keep this comment", config_bytes.decode())
        policy = (target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# Existing project instructions\nKeep this paragraph.", policy)
        self.assertEqual(policy.count("<!-- BEGIN LUNA WORKER SETUP POLICY -->"), 1)

        for relative, contents in original.items():
            backups = list((target / relative).parent.glob((target / relative).name + ".bak-*"))
            self.assertEqual(len(backups), 1, f"expected one backup for {relative}")
            self.assertEqual(backups[0].read_bytes(), contents)

        verify = self.command(self.verifier, "--target", str(target))
        self.assertEqual(verify.returncode, 0, verify.stderr)
        self.assertIn("Static validation passed", verify.stdout)
        self.assertIn("Start a new Codex session", verify.stdout)

        installed_skill = target / "skills" / "delegate-bounded-work" / "SKILL.md"
        installed_skill.write_text("unexpected replacement\n", encoding="utf-8")
        mismatch = self.command(self.verifier, "--target", str(target))
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("does not match the package", mismatch.stderr)
        installed_skill.write_bytes((self.package / "skills" / "delegate-bounded-work" / "SKILL.md").read_bytes())

        installed = {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file() and ".bak-" not in path.name}
        backup_count = len(list(target.rglob("*.bak-*")))
        second = self.command(self.installer, "--target", str(target), "--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("No changes", second.stdout)
        self.assertEqual(
            {path.relative_to(target): path.read_bytes() for path in target.rglob("*") if path.is_file() and ".bak-" not in path.name},
            installed,
        )
        self.assertEqual(len(list(target.rglob("*.bak-*"))), backup_count)

    def test_project_scope_installs_to_project_codex_home(self) -> None:
        project = self.root / "project-target"
        project.mkdir()
        result = self.command(self.installer, "--scope", "project", "--target", str(project), "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((project / ".codex" / "config.toml").is_file())
        self.assertTrue((project / ".codex" / "agents" / "luna-worker.toml").is_file())
        self.assertTrue((project / ".codex" / "skills" / "delegate-bounded-work" / "SKILL.md").is_file())
        self.assertTrue((project / "AGENTS.md").is_file())
        verify = self.command(self.verifier, "--scope", "project", "--target", str(project))
        self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_invalid_and_ambiguous_toml_abort_without_target_changes(self) -> None:
        cases = {
            "invalid": b"[agents\nenabled = true\n",
            "repeated-table": b"[agents]\nenabled = false\n\n[agents]\nmax_concurrent_threads_per_session = 1\n",
            "duplicate-key": b"[agents]\nenabled = false\nenabled = true\n",
            "inline-agents-table": b'agents = { enabled = true }\n',
        }
        for label, config_bytes in cases.items():
            with self.subTest(label=label):
                target = self.root / f"bad-{label}"
                target.mkdir()
                config_path = target / "config.toml"
                config_path.write_bytes(config_bytes)
                result = self.command(self.installer, "--target", str(target), "--apply")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(config_path.read_bytes(), config_bytes)
                self.assertEqual(list(target.rglob("*.bak-*")), [])
                self.assertFalse((target / "AGENTS.md").exists())
                self.assertFalse((target / "agents" / "luna-worker.toml").exists())

    def test_ambiguous_policy_markers_abort_without_installing_other_files(self) -> None:
        target = self.root / "bad-policy"
        target.mkdir()
        policy = target / "AGENTS.md"
        marker = "<!-- BEGIN LUNA WORKER SETUP POLICY -->"
        policy.write_text(f"{marker}\nfirst\n{marker}\nsecond\n", encoding="utf-8")
        original = policy.read_bytes()

        result = self.command(self.installer, "--target", str(target), "--apply")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(policy.read_bytes(), original)
        self.assertFalse((target / "config.toml").exists())
        self.assertFalse((target / "agents" / "luna-worker.toml").exists())
        self.assertEqual(list(target.rglob("*.bak-*")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
