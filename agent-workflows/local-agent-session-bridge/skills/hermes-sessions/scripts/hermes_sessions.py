#!/usr/bin/env python3
"""Find, read, and message Hermes Agent sessions on this machine.

Reads ~/.hermes/state.db read-only. Sends by resuming the session with
`hermes --resume <ID> -z <message>`, which appends a turn to that same session.

  hermes_sessions.py list [--search TEXT] [--limit N] [--all]
  hermes_sessions.py read ID [--last N]
  hermes_sessions.py send ID MESSAGE [--force] [--dry-run]
"""
import argparse
import datetime as dt
import os
import shutil
import sqlite3
import subprocess
import sys
import time

DB = os.path.expanduser("~/.hermes/state.db")
HERMES = shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")
# Machine-generated sessions hidden from `list` unless --all.
NOISE_SOURCES = {"cron", "subagent"}
RECENT_SECONDS = 5 * 60
SENDER_TAG = f"[Message from {os.environ.get('SESSION_BRIDGE_SENDER', 'another agent')} via hermes-sessions]"


def connect():
    if not os.path.exists(DB):
        sys.exit(f"Hermes session store not found: {DB}")
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def when(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"


def get_session(con, sid):
    row = con.execute(
        "SELECT id, source, title, cwd, COALESCE(last_activity_at, started_at), message_count "
        "FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        sys.exit(f"No Hermes session with ID {sid}. Run `list` to find it.")
    return row


def cmd_list(args):
    con = connect()
    where, params = ["hidden = 0", "archived = 0"], []
    if not args.all:
        where.append(f"source NOT IN ({','.join('?' * len(NOISE_SOURCES))})")
        params += sorted(NOISE_SOURCES)
    if args.search:
        like = f"%{args.search}%"
        where.append("(title LIKE ? OR id IN (SELECT session_id FROM messages "
                     "WHERE role IN ('user','assistant') AND content LIKE ?))")
        params += [like, like]
    rows = con.execute(
        "SELECT id, source, COALESCE(last_activity_at, started_at) AS act, message_count, title "
        f"FROM sessions WHERE {' AND '.join(where)} ORDER BY act DESC LIMIT ?",
        params + [args.limit]).fetchall()
    if not rows:
        print("No matching Hermes sessions.")
        return
    print(f"{'ID':<24} {'SOURCE':<9} {'LAST ACTIVE':<16} {'MSGS':>5}  TITLE")
    for sid, source, act, n, title in rows:
        print(f"{sid:<24} {source:<9} {when(act):<16} {n or 0:>5}  {(title or '-')[:70]}")


def cmd_read(args):
    con = connect()
    sid, source, title, cwd, act, _ = get_session(con, args.id)
    rows = con.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? "
        "AND role IN ('user','assistant') AND content IS NOT NULL AND TRIM(content) != '' "
        "ORDER BY id DESC LIMIT ?", (sid, args.last)).fetchall()
    print(f"# Hermes session {sid}\nTitle: {title or '-'}\nSource: {source}  Last active: {when(act)}"
          f"  Folder: {cwd or '-'}\nShowing last {len(rows)} user/assistant messages.\n")
    for role, content, ts in reversed(rows):
        print(f"--- {role.upper()} ({when(ts)}) ---\n{content.strip()}\n")


def cmd_send(args):
    con = connect()
    sid, source, title, _, act, _ = get_session(con, args.id)
    con.close()
    if act and time.time() - act < RECENT_SECONDS and not args.force:
        sys.exit(f"Refused: {sid} was active {int(time.time() - act)}s ago and may be mid-turn. "
                 "Wait, or re-run with --force if the user approved.")
    if args.dry_run:
        print(f"Dry run: would send to Hermes session {sid} ({source}, {title or '-'}).")
        return
    print(f"Sending to Hermes session {sid} ({title or '-'})...", file=sys.stderr)
    proc = subprocess.run([HERMES, "--resume", sid, "-z", f"{SENDER_TAG}\n\n{args.message}"],
                          capture_output=True, text=True, timeout=args.timeout)
    if proc.returncode != 0:
        sys.exit(f"hermes exited {proc.returncode}:\n{proc.stderr.strip()[-2000:]}")
    print(proc.stdout.strip())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list", help="List recent Hermes sessions")
    s.add_argument("--search", help="Match title or message text (case-insensitive)")
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--all", action="store_true", help="Include cron and subagent sessions")
    s.set_defaults(func=cmd_list)
    s = sub.add_parser("read", help="Print a session's recent history")
    s.add_argument("id")
    s.add_argument("--last", type=int, default=30, help="Number of user/assistant messages")
    s.set_defaults(func=cmd_read)
    s = sub.add_parser("send", help="Add a message to a session and print the agent's reply")
    s.add_argument("id")
    s.add_argument("message")
    s.add_argument("--force", action="store_true", help="Allow sessions active in the last 5 minutes")
    s.add_argument("--dry-run", action="store_true", help="Run the checks without sending")
    s.add_argument("--timeout", type=int, default=600)
    s.set_defaults(func=cmd_send)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
