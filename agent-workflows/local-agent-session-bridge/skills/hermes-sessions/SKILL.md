---
name: hermes-sessions
description: Find, read, and message existing Hermes Agent sessions on this machine. Use when the user refers to something discussed with Hermes, asks what Hermes said or did, or asks you to tell, ask, or hand something to Hermes in a particular session.
---

# Hermes Sessions

Script: `python3 <this-skill>/scripts/hermes_sessions.py` (Python 3 standard library only). Set `SESSION_BRIDGE_SENDER` to your agent's name (for example `Claude Code`) so messages are labeled correctly.

## Steps

1. **Find the session.** `list --search "<topic words>"` (add `--all` to include cron and subagent runs; `--limit N`). With no clue, plain `list` shows the most recent sessions.
2. **Confirm the match.** `read <ID> --last 20`. If more than one session plausibly fits, show the user the candidates (ID, title, last active) and ask which one. Do not guess.
3. **Before sending, show the user the session ID, its title, and the exact message, and get a yes.** Skip this only when the user named the session ID and gave the message text.
4. **Send.** `send <ID> "<message>"`. The script labels the message with the sender, resumes that same session with `hermes --resume <ID> -z`, and prints the reply. Relay it to the user.

## Guards

- Sessions active in the last 5 minutes are refused unless `--force` is passed, because Hermes may be mid-turn. Use `--force` only with the user's approval.
- `--dry-run` runs the checks and names the target without sending.
- Reading never changes anything: `~/.hermes/state.db` is opened read-only.

## Notes

- Gateway sessions (Telegram and other platforms) can be messaged. The turn is stored in that session's history, but nothing is posted to the chat platform itself, so the user only sees the reply you relay.
- Hermes's own MCP server (`hermes mcp serve`) lists platform chats, not individual sessions, so this script reads the session store instead.
- A send runs with Hermes's model and may use Hermes's tools under its own approval settings.
