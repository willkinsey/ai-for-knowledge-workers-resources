#!/usr/bin/env python3
"""Install the Luna Worker Setup Kit. Dry-run is the default."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from common import (
    AGENTS_END,
    AGENTS_START,
    SKILL_SOURCE,
    SetupError,
    count_managed_policy_blocks,
    expected_policy_text,
    load_template,
    merge_agents_config,
    _parse_toml,
    resolve_target,
)


@dataclass(frozen=True)
class PlannedFile:
    name: str
    path: Path
    content: bytes
    original: bytes | None

    @property
    def changed(self) -> bool:
        return self.original != self.content


def build_policy(existing: bytes | None, path: Path) -> bytes:
    expected = expected_policy_text()
    starts, ends = count_managed_policy_blocks(expected)
    if starts != 1 or ends != 1 or expected.index(AGENTS_START) >= expected.index(AGENTS_END):
        raise SetupError("The AGENTS policy template must contain one correctly ordered managed block.")

    if existing is None:
        return expected.encode("utf-8")
    try:
        text = existing.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"Cannot safely edit non-UTF-8 AGENTS file: {path}") from exc

    start_count, end_count = count_managed_policy_blocks(text)
    if start_count != end_count or start_count > 1:
        raise SetupError(f"Ambiguous Luna policy markers in {path}; no files were changed.")
    if start_count == 0:
        if not text:
            return expected.encode("utf-8")
        separator = "" if text.endswith(("\n", "\r")) else "\n"
        if text.endswith(("\n\n", "\r\n\r\n")):
            separator = ""
        return (text + separator + expected).encode("utf-8")

    start = text.index(AGENTS_START)
    end = text.index(AGENTS_END)
    if start >= end:
        raise SetupError(f"Luna policy markers are out of order in {path}; no files were changed.")
    end += len(AGENTS_END)
    if text.startswith("\r\n", end):
        end += 2
    elif text.startswith(("\n", "\r"), end):
        end += 1
    before = text[:start]
    after = text[end:]
    return (before + expected + after).encode("utf-8")


def _validate_package() -> None:
    load_template("config-agents.toml")
    role_template = load_template("luna-worker.toml")
    role_data = _parse_toml(role_template, Path("templates/luna-worker.toml"))
    expected_role = {
        "name": "luna_worker",
        "description": role_data.get("description"),
        "model": "gpt-6-luna",
        "model_reasoning_effort": "max",
        "developer_instructions": role_data.get("developer_instructions"),
    }
    if role_data != expected_role or not isinstance(role_data.get("description"), str) or not role_data["description"].strip():
        raise SetupError("The luna-worker.toml template has unexpected role fields or values.")
    instructions = role_data["developer_instructions"]
    if not isinstance(instructions, str) or "Do not delegate further." not in instructions:
        raise SetupError("The Luna role template must prohibit further delegation.")
    if "Do not push, merge, rebase, deploy" not in instructions:
        raise SetupError("The Luna role template is missing the required authority boundary.")
    policy = expected_policy_text().encode("utf-8")
    skill_path = SKILL_SOURCE / "SKILL.md"
    if not SKILL_SOURCE.is_dir() or not skill_path.is_file():
        raise SetupError(f"Required runtime skill is missing from the package: {skill_path}")


def _read_target(path: Path) -> bytes | None:
    if path.is_symlink():
        raise SetupError(f"Refusing to replace a symbolic link: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise SetupError(f"Managed target is not a regular file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SetupError(f"Cannot read managed target {path}: {exc}") from exc


def _check_parent_paths(root: Path, paths: dict[str, Path], scope: str) -> None:
    for path in paths.values():
        parent = path.parent
        while parent != root and parent != parent.parent:
            if parent.exists() and parent.is_symlink():
                raise SetupError(f"Refusing to write through a symbolic-link directory: {parent}")
            parent = parent.parent
    if scope == "project":
        codex_dir = root / ".codex"
        if codex_dir.exists() and codex_dir.is_symlink():
            raise SetupError(f"Refusing to write through a symbolic-link directory: {codex_dir}")


def _build_plan(scope: str, root: Path, targets: dict[str, Path]) -> list[PlannedFile]:
    _validate_package()
    _check_parent_paths(root, targets, scope)

    raw_by_name = {name: _read_target(path) for name, path in targets.items()}
    config_content = merge_agents_config(raw_by_name["config"], targets["config"])
    policy_content = build_policy(raw_by_name["policy"], targets["policy"])
    role_content = load_template("luna-worker.toml")
    skill_content = (SKILL_SOURCE / "SKILL.md").read_bytes()

    content_by_name = {
        "config": config_content,
        "role": role_content,
        "policy": policy_content,
        "skill": skill_content,
    }
    return [
        PlannedFile(name=name, path=targets[name], content=content_by_name[name], original=raw_by_name[name])
        for name in ("config", "role", "policy", "skill")
    ]


def _backup_path(path: Path, timestamp: str) -> Path:
    base = path.with_name(f"{path.name}.bak-{timestamp}")
    candidate = base
    index = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak-{timestamp}-{index}")
        index += 1
    return candidate


def _make_backup(item: PlannedFile, timestamp: str) -> Path:
    assert item.original is not None
    current = _read_target(item.path)
    if current != item.original:
        raise SetupError(f"Target changed during preflight; stopped before writing: {item.path}")
    backup = _backup_path(item.path, timestamp)
    try:
        backup.write_bytes(item.original)
        if item.path.exists():
            shutil.copystat(item.path, backup, follow_symlinks=False)
    except OSError as exc:
        try:
            backup.unlink(missing_ok=True)
        except OSError:
            pass
        raise SetupError(f"Could not create backup for {item.path}: {exc}") from exc
    return backup


def _atomic_write(item: PlannedFile) -> None:
    current = _read_target(item.path)
    if current != item.original:
        raise SetupError(f"Target changed during installation; stopped before writing: {item.path}")
    item.path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=item.path.parent, prefix=f".{item.path.name}.", delete=False) as handle:
            handle.write(item.content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if item.original is not None:
            mode = item.path.stat().st_mode & 0o777
            temp_path.chmod(mode)
        os.replace(temp_path, item.path)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise SetupError(f"Could not write {item.path}: {exc}") from exc


def _print_plan(plan: list[PlannedFile], scope: str, root: Path, apply: bool) -> None:
    print(f"Scope: {scope}")
    print(f"Target root: {root}")
    changes = [item for item in plan if item.changed]
    if not changes:
        print("No changes: all managed files already match the package.")
    else:
        for item in changes:
            verb = "Create" if item.original is None else "Update"
            print(f"{verb}: {item.path}")
            if item.original is not None:
                print(f"  Backup existing file as: {item.path.name}.bak-<UTC timestamp>")
    if apply:
        print("Mode: apply")
    else:
        print("Mode: dry-run. Pass --apply to write these changes.")


def run(scope: str, target: str | None, apply: bool) -> int:
    root, targets = resolve_target(scope, target)
    plan = _build_plan(scope, root, targets)
    _print_plan(plan, scope, root, apply)
    changes = [item for item in plan if item.changed]
    if not apply or not changes:
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    for item in changes:
        item.path.parent.mkdir(parents=True, exist_ok=True)
    backups: dict[Path, Path] = {}
    for item in changes:
        if item.original is not None:
            backups[item.path] = _make_backup(item, timestamp)
    written: list[PlannedFile] = []
    try:
        for item in changes:
            _atomic_write(item)
            written.append(item)
    except SetupError as exc:
        # Restore only files still containing this install's content.
        for item in reversed(written):
            try:
                if _read_target(item.path) == item.content:
                    backup = backups.get(item.path)
                    if backup is not None:
                        restore = PlannedFile(item.name, item.path, item.original or b"", item.content)
                        _atomic_write(restore)
                    else:
                        item.path.unlink(missing_ok=True)
            except (OSError, SetupError):
                pass
        raise exc

    print(f"Applied {len(changes)} file change(s).")
    for path, backup in backups.items():
        print(f"Backup: {backup}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the Luna Worker Setup Kit (dry-run by default).")
    parser.add_argument("--scope", choices=("user", "project"), default="user", help="user Codex home or project-local setup")
    parser.add_argument("--target", help="Codex home for user scope, or existing project root for project scope")
    parser.add_argument("--apply", action="store_true", help="write the displayed changes")
    args = parser.parse_args(argv)
    try:
        return run(args.scope, args.target, args.apply)
    except (SetupError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
