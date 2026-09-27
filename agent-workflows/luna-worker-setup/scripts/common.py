"""Shared paths and validation helpers for the Luna Worker Setup Kit."""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PACKAGE_ROOT / "templates"
SKILL_SOURCE = PACKAGE_ROOT / "skills" / "delegate-bounded-work"

AGENTS_START = "<!-- BEGIN LUNA WORKER SETUP POLICY -->"
AGENTS_END = "<!-- END LUNA WORKER SETUP POLICY -->"

OWNED_AGENT_VALUES: dict[str, Any] = {
    "enabled": True,
    "max_concurrent_threads_per_session": 3,
    "default_subagent_model": "gpt-6-luna",
    "default_subagent_reasoning_effort": "max",
}

_AGENTS_HEADER = re.compile(r"^\s*\[\s*agents\s*\]\s*(?:#.*)?$")
_ANY_TABLE_HEADER = re.compile(r"^\s*\[\[?.*?\]\]?\s*(?:#.*)?$")


class SetupError(Exception):
    """A safe, user-actionable setup or validation failure."""


def package_file(relative_path: str) -> Path:
    return PACKAGE_ROOT / relative_path


def load_template(name: str) -> bytes:
    path = TEMPLATE_DIR / name
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SetupError(f"Required package template is unavailable: {path} ({exc})") from exc


def resolve_target(scope: str, target: str | None) -> tuple[Path, dict[str, Path]]:
    """Resolve the destination root and the four managed runtime files."""
    if scope == "user":
        if target is not None:
            root = Path(target).expanduser().resolve()
        else:
            codex_home = os.environ.get("CODEX_HOME")
            root = Path(codex_home).expanduser().resolve() if codex_home else (Path.home() / ".codex").resolve()
        base = root
    elif scope == "project":
        if target is None:
            raise SetupError("Project scope requires --target with an existing project root.")
        root = Path(target).expanduser().resolve()
        if not root.is_dir():
            raise SetupError(f"Project scope target must be an existing directory: {root}")
        base = root / ".codex"
    else:
        raise SetupError(f"Unsupported scope: {scope}")

    paths = {
        "config": base / "config.toml",
        "role": base / "agents" / "luna-worker.toml",
        "policy": root / "AGENTS.md",
        "skill": base / "skills" / "delegate-bounded-work" / "SKILL.md",
    }
    return root, paths


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return ""


def _advance_multiline_string(line: str, active: str | None) -> str | None:
    """Track TOML multiline strings so header-looking string content is ignored."""
    i = 0
    while i < len(line):
        if active is not None:
            end = line.find(active, i)
            if end < 0:
                return active
            if active == '"""' and end > 0 and line[end - 1] == "\\":
                i = end + 1
                continue
            i = end + 3
            active = None
            continue

        char = line[i]
        if char == "#":
            return None
        if line.startswith('"""', i):
            active = '"""'
            i += 3
            continue
        if line.startswith("'''", i):
            active = "'''"
            i += 3
            continue
        if char in "\"'":
            quote = char
            i += 1
            while i < len(line):
                if quote == '"' and line[i] == "\\":
                    i += 2
                    continue
                if line[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        i += 1
    return active


def _visible_lines(text: str) -> list[tuple[int, str]]:
    """Return source lines that are outside TOML multiline strings."""
    result: list[tuple[int, str]] = []
    active: str | None = None
    for index, line in enumerate(text.splitlines(), start=0):
        was_in_string = active is not None
        if not was_in_string:
            result.append((index, line))
        active = _advance_multiline_string(line, active)
    return result


def _header_indices(text: str) -> list[tuple[int, str]]:
    return [(index, line) for index, line in _visible_lines(text) if _ANY_TABLE_HEADER.match(line)]


def _agents_header_indices(text: str) -> list[int]:
    return [index for index, line in _visible_lines(text) if _AGENTS_HEADER.match(line)]


def _parse_toml(raw: bytes, display_path: Path) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = tomllib.loads(text)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SetupError(f"Invalid TOML in {display_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SetupError(f"TOML root must be a table in {display_path}.")
    return value


def parse_agents_template() -> dict[str, Any]:
    template = load_template("config-agents.toml")
    value = _parse_toml(template, TEMPLATE_DIR / "config-agents.toml")
    agents = value.get("agents")
    if not isinstance(agents, dict) or agents != OWNED_AGENT_VALUES:
        raise SetupError("The config-agents.toml template does not contain the exact supported Luna defaults.")
    return agents


def count_managed_policy_blocks(text: str) -> tuple[int, int]:
    return text.count(AGENTS_START), text.count(AGENTS_END)


def expected_policy_text() -> str:
    raw = load_template("AGENTS-luna-policy.md")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError("The AGENTS policy template is not valid UTF-8.") from exc


def _split_toml_comment(value: str) -> tuple[str, str]:
    """Split a one-line TOML value from its comment, respecting quoted strings."""
    i = 0
    quote: str | None = None
    triple = False
    while i < len(value):
        if quote is None:
            if value[i] == "#":
                comment_start = i
                while comment_start > 0 and value[comment_start - 1].isspace():
                    comment_start -= 1
                return value[:comment_start], value[comment_start:]
            if value.startswith('"""', i):
                quote, triple = '"', True
                i += 3
                continue
            if value.startswith("'''", i):
                quote, triple = "'", True
                i += 3
                continue
            if value[i] == '"':
                quote, triple = '"', False
            elif value[i] == "'":
                quote, triple = "'", False
            i += 1
            continue

        if quote == '"' and value[i] == "\\":
            i += 2
            continue
        if triple and value.startswith(quote * 3, i):
            quote, triple = None, False
            i += 3
            continue
        if not triple and value[i] == quote:
            quote = None
        i += 1
    return value, ""


def _assignment_key(line: str, owned_keys: set[str]) -> tuple[str, re.Match[str]] | None:
    for key in owned_keys:
        quoted = re.escape(key)
        pattern = re.compile(rf"^(?P<prefix>\s*(?:{quoted}|\"{quoted}\"|'{quoted}')\s*=\s*)(?P<rhs>.*?)(?P<ending>\r?\n|\r)?$")
        match = pattern.match(line)
        if match:
            return key, match
    return None


def merge_agents_config(existing: bytes | None, config_path: Path) -> bytes:
    """Merge the four owned values while preserving all other TOML text."""
    values = parse_agents_template()
    template_text = load_template("config-agents.toml").decode("utf-8")
    if existing is None:
        return template_text.encode("utf-8")

    text = existing.decode("utf-8")
    parsed = _parse_toml(existing, config_path)
    table_indices = _agents_header_indices(text)
    if len(table_indices) > 1:
        raise SetupError(f"Ambiguous repeated [agents] tables in {config_path}; no files were changed.")

    parsed_agents = parsed.get("agents")
    if parsed_agents is not None and not table_indices:
        raise SetupError(
            f"The agents settings in {config_path} use an inline, dotted, or unsupported table form; "
            "the installer cannot preserve them safely. No files were changed."
        )
    if not table_indices:
        separator = "" if not text else ("\n" if text.endswith(("\n", "\r")) else "\n\n")
        if text and text.endswith(("\n\n", "\r\n\r\n")):
            separator = ""
        addition = separator + template_text
        return (text + addition).encode("utf-8")

    if not isinstance(parsed_agents, dict):
        raise SetupError(f"The [agents] value in {config_path} is not a table; no files were changed.")
    for key in values:
        if isinstance(parsed_agents.get(key), dict):
            raise SetupError(
                f"The owned key {key!r} in {config_path} has child keys that cannot be preserved; no files were changed."
            )

    lines = text.splitlines(keepends=True)
    start = table_indices[0]
    table_end = len(lines)
    for index, line in _header_indices(text):
        if index > start:
            table_end = index
            break

    found: dict[str, int] = {}
    key_set = set(values)
    for index in range(start + 1, table_end):
        assignment = _assignment_key(lines[index], key_set)
        if assignment is None:
            continue
        key, match = assignment
        if key in found:
            raise SetupError(f"Duplicate owned key {key!r} in {config_path}; no files were changed.")
        found[key] = index

    for key in values:
        if key in parsed_agents and key not in found:
            raise SetupError(
                f"The owned key {key!r} in {config_path} cannot be located unambiguously; no files were changed."
            )

    for key, index in found.items():
        assignment = _assignment_key(lines[index], key_set)
        assert assignment is not None
        _, match = assignment
        rhs = match.group("rhs")
        value_text, comment = _split_toml_comment(rhs)
        # Multiline values need structural editing beyond this narrow owned-key merge.
        if any(delimiter in value_text for delimiter in ('"""', "'''")):
            if not (
                value_text.count('"""') == 2 or value_text.count("'''") == 2
            ):
                raise SetupError(
                    f"The owned key {key!r} in {config_path} uses a multiline value; no files were changed."
                )
        newline = match.group("ending") or ""
        lines[index] = match.group("prefix") + _toml_value(values[key]) + comment + newline

    missing = [key for key in values if key not in found]
    if missing:
        newline = _preferred_newline(lines)
        inserted = [f"{key} = {_toml_value(values[key])}{newline}" for key in missing]
        if table_end > start + 1 and not _line_ending(lines[table_end - 1]):
            lines[table_end - 1] += newline
        if table_end == len(lines) and lines and not _line_ending(lines[-1]):
            lines[-1] += newline
        lines[table_end:table_end] = inserted
        # Preserve a no-final-newline source when the inserted lines end the file.
        if table_end == len(lines) - len(inserted) and lines and not text.endswith(("\n", "\r")):
            lines[-1] = lines[-1].rstrip("\r\n")

    result = "".join(lines)
    # Validate the produced TOML and owned values before permitting any filesystem writes.
    result_table = _parse_toml(result.encode("utf-8"), config_path).get("agents")
    if not isinstance(result_table, dict) or any(result_table.get(key) != value for key, value in values.items()):
        raise SetupError(f"The merged [agents] table in {config_path} did not validate; no files were changed.")
    return result.encode("utf-8")


def _toml_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    raise SetupError(f"Unsupported TOML value in package template: {value!r}")


def _preferred_newline(lines: list[str]) -> str:
    for line in lines:
        ending = _line_ending(line)
        if ending:
            return ending
    return "\n"
