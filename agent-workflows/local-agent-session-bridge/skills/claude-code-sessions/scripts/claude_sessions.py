#!/usr/bin/env python3
"""Find, read, and message Claude Code sessions on this Mac.

Reads transcripts in ~/.claude/projects/<project>/<session-id>.jsonl (read-only).
Sends by resuming the session from its recorded folder with
`claude --resume <ID> -p <message>`, which appends a turn to that same session.

  claude_sessions.py list [--search TEXT] [--limit N]
  claude_sessions.py read ID [--last N]
  claude_sessions.py send ID MESSAGE [--force] [--dry-run] [--model M]
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

PROJECTS = os.path.expanduser("~/.claude/projects")
CLAUDE = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
RECENT_SECONDS = 10 * 60
SENDER_TAG = f"[Message from {os.environ.get('SESSION_BRIDGE_SENDER', 'another agent')} via claude-sessions]"
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def when(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def text_of(message):
    """Plain text of a user/assistant message; tool calls and results are skipped."""
    content = (message or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    else:
        parts = [c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text"]
    return REMINDER.sub("", "\n".join(parts)).strip()


def load(path):
    """Summarize one transcript: title, folder, launch type, and its text turns."""
    info = {"id": os.path.basename(path)[:-6], "path": path, "mtime": os.path.getmtime(path),
            "title": None, "cwd": None, "app": False, "turns": []}
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get("type")
            if t == "custom-title":
                info["title"] = d.get("customTitle") or info["title"]
            elif t in ("agent-name", "bridge-session"):
                # Sessions the desktop app manages carry one of these records; `claude -p`
                # runs started from inside the app also say entrypoint=claude-desktop, so
                # that field cannot tell them apart.
                info["app"] = True
            elif t in ("user", "assistant") and not d.get("isSidechain"):
                info["cwd"] = info["cwd"] or d.get("cwd")
                text = text_of(d.get("message"))
                if text:
                    info["turns"].append((t, d.get("timestamp", ""), text))
    if not info["title"]:
        first = next((x for r, _, x in info["turns"] if r == "user"), "")
        info["title"] = " ".join(first.split())[:70] or "-"
    return info


def kind(s):
    return "desktop-app" if s["app"] else "cli"


def all_sessions():
    paths = glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
    return sorted((load(p) for p in paths), key=lambda s: s["mtime"], reverse=True)


def find(sid):
    paths = glob.glob(os.path.join(PROJECTS, "*", f"{sid}.jsonl"))
    if not paths:
        sys.exit(f"No Claude Code session with ID {sid}. Run `list` to find it.")
    return load(paths[0])


def cmd_list(args):
    rows = all_sessions()
    if args.search:
        needle = args.search.lower()
        rows = [s for s in rows if needle in s["title"].lower()
                or any(needle in x.lower() for _, _, x in s["turns"])]
    rows = rows[:args.limit]
    if not rows:
        print("No matching Claude Code sessions.")
        return
    print(f"{'ID':<36}  {'KIND':<11} {'LAST ACTIVE':<16} {'TURNS':>5}  TITLE")
    for s in rows:
        print(f"{s['id']:<36}  {kind(s):<11} {when(s['mtime']):<16} "
              f"{len(s['turns']):>5}  {s['title'][:70]}")


def cmd_read(args):
    s = find(args.id)
    turns = s["turns"][-args.last:]
    print(f"# Claude Code session {s['id']}\nTitle: {s['title']}\nKind: {kind(s)}"
          f"  Last active: {when(s['mtime'])}\nFolder: {s['cwd'] or '-'}\n"
          f"Showing last {len(turns)} user/assistant messages.\n")
    for role, ts, text in turns:
        print(f"--- {role.upper()} ({ts[:16].replace('T', ' ')} UTC) ---\n{text}\n")


def cmd_send(args):
    s = find(args.id)
    age = time.time() - s["mtime"]
    if age < RECENT_SECONDS and not args.force:
        sys.exit(f"Refused: {s['id']} was active {int(age)}s ago and may be in use. "
                 "Wait, or re-run with --force if the user approved.")
    if not s["cwd"] or not os.path.isdir(s["cwd"]):
        sys.exit(f"Refused: the session's folder is missing ({s['cwd']}); `claude --resume` "
                 "only finds a session from the folder it was started in.")
    if args.dry_run:
        print(f"Dry run: would send to Claude Code session {s['id']} ({kind(s)}, {s['title']}).")
        return
    cmd = [CLAUDE, "--resume", s["id"], "-p", f"{SENDER_TAG}\n\n{args.message}"]
    if args.model:
        cmd += ["--model", args.model]
    print(f"Sending to Claude Code session {s['id']} ({s['title']})...", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=s["cwd"], capture_output=True, text=True, timeout=args.timeout)
    if proc.returncode != 0:
        sys.exit(f"claude exited {proc.returncode}:\n{proc.stderr.strip()[-2000:]}")
    print(proc.stdout.strip())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", help="List recent Claude Code sessions")
    s.add_argument("--search", help="Match title or message text (case-insensitive)")
    s.add_argument("--limit", type=int, default=15)
    s.set_defaults(func=cmd_list)
    s = sub.add_parser("read", help="Print a session's recent history")
    s.add_argument("id")
    s.add_argument("--last", type=int, default=30, help="Number of user/assistant messages")
    s.set_defaults(func=cmd_read)
    s = sub.add_parser("send", help="Add a message to a session and print Claude's reply")
    s.add_argument("id")
    s.add_argument("message")
    s.add_argument("--force", action="store_true", help="Allow sessions active in the last 10 minutes")
    s.add_argument("--dry-run", action="store_true", help="Run the checks without sending")
    s.add_argument("--model", help="Model for this turn, e.g. haiku or sonnet")
    s.add_argument("--timeout", type=int, default=900)
    s.set_defaults(func=cmd_send)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
