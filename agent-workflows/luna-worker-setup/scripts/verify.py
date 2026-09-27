#!/usr/bin/env python3
"""Statically verify the installed Luna Worker Setup configuration."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from common import (
    AGENTS_END,
    AGENTS_START,
    SetupError,
    _agents_header_indices,
    _parse_toml,
    count_managed_policy_blocks,
    expected_policy_text,
    load_template,
    package_file,
    parse_agents_template,
    resolve_target,
)


def _read(path: Path, label: str) -> bytes:
    if path.is_symlink():
        raise SetupError(f"{label} must be a regular file, not a symbolic link: {path}")
    if not path.is_file():
        raise SetupError(f"Missing {label}: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SetupError(f"Cannot read {label} {path}: {exc}") from exc


def _verify_config(path: Path) -> None:
    raw = _read(path, "Codex config")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"Codex config is not valid UTF-8: {path}") from exc
    sections = _agents_header_indices(text)
    if len(sections) != 1:
        raise SetupError(f"Expected exactly one [agents] table in {path}; found {len(sections)}.")
    actual = _parse_toml(raw, path)
    agents = actual.get("agents")
    expected = parse_agents_template()
    if not isinstance(agents, dict):
        raise SetupError(f"[agents] table is missing or invalid in {path}.")
    mismatches = [key for key, value in expected.items() if agents.get(key) != value]
    if mismatches:
        details = ", ".join(f"{key} should be {expected[key]!r}" for key in mismatches)
        raise SetupError(f"Owned [agents] values do not match in {path}: {details}.")


def _verify_role(path: Path) -> None:
    actual = _parse_toml(_read(path, "Luna agent role"), path)
    template = _parse_toml(load_template("luna-worker.toml"), Path("templates/luna-worker.toml"))
    if actual != template:
        expected_fields = ("name", "description", "model", "model_reasoning_effort", "developer_instructions")
        differences = [key for key in expected_fields if actual.get(key) != template.get(key)]
        if not differences and actual.keys() != template.keys():
            differences = ["unexpected role field set"]
        raise SetupError(f"Luna role values do not match the package in {path}: {', '.join(differences)}.")
    if actual.get("name") != "luna_worker" or actual.get("model") != "gpt-6-luna" or actual.get("model_reasoning_effort") != "max":
        raise SetupError(f"Luna role must be luna_worker on gpt-6-luna at max reasoning: {path}.")


def _verify_policy(path: Path) -> None:
    raw = _read(path, "AGENTS policy file")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError(f"AGENTS policy file is not valid UTF-8: {path}") from exc
    starts, ends = count_managed_policy_blocks(text)
    expected = expected_policy_text()
    if starts != 1 or ends != 1 or text.count(expected) != 1:
        raise SetupError(
            f"Expected exactly one intact Luna policy block in {path}; found {starts} start marker(s) and {ends} end marker(s)."
        )
    if text.index(AGENTS_START) >= text.index(AGENTS_END):
        raise SetupError(f"Luna policy markers are out of order in {path}.")


def _verify_skill(path: Path) -> None:
    raw = _read(path, "delegate-bounded-work runtime skill")
    expected_path = package_file("skills/delegate-bounded-work/SKILL.md")
    try:
        expected = expected_path.read_bytes()
    except OSError as exc:
        raise SetupError(f"Packaged runtime skill is unavailable: {expected_path} ({exc})") from exc
    if raw != expected:
        raise SetupError(f"delegate-bounded-work runtime skill does not match the package: {path}")


def run(scope: str, target: str | None) -> int:
    _root, paths = resolve_target(scope, target)
    _verify_config(paths["config"])
    _verify_role(paths["role"])
    _verify_policy(paths["policy"])
    _verify_skill(paths["skill"])
    print("Static validation passed: TOML syntax and Luna settings, role, managed AGENTS policy block, and runtime skill are present.")
    print("Start a new Codex session before the live smoke test; static validation does not prove which model or effort a child actually used.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only static verification of a Luna Worker Setup installation.")
    parser.add_argument("--scope", choices=("user", "project"), default="user", help="user Codex home or project-local setup")
    parser.add_argument("--target", help="Codex home for user scope, or existing project root for project scope")
    args = parser.parse_args(argv)
    try:
        return run(args.scope, args.target)
    except (SetupError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
