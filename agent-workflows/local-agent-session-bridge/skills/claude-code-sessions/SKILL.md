---
name: claude-code-sessions
description: Find, read, and message existing Claude Code sessions on this machine. Use when the user refers to work done in Claude Code, asks what Claude said or did, or asks you to tell, ask, or hand something to Claude in a particular session.
---

# Claude Code Sessions

Script: `python3 <this-skill>/scripts/claude_sessions.py` (Python 3 standard library only). Set `SESSION_BRIDGE_SENDER` to your agent's name (for example `Hermes`) so messages are labeled correctly.

## Steps

1. **Find the session.** `list --search "<topic words>"` (`--limit N`). With no clue, plain `list` shows the most recent sessions. `KIND` shows `desktop-app` for sessions managed by the Claude desktop app and `cli` for command-line sessions.
2. **Confirm the match.** `read <ID> --last 20`. If more than one session plausibly fits, show the user the candidates (ID, title, last active) and ask which one. Do not guess.
3. **Before sending, show the user the session ID, its title, and the exact message, and get a yes.** Skip this only when the user named the session ID and gave the message text.
4. **Send.** `send <ID> "<message>"` (optionally `--model haiku|sonnet|opus`). The script labels the message with the sender, runs `claude --resume <ID> -p` from the session's own folder, and prints Claude's reply. Relay the reply to the user.

## Guards

- Sessions active in the last 10 minutes are refused unless `--force` is passed, because they may be in use. Use `--force` only with the user's approval.
- `--dry-run` runs the checks and names the target without sending.
- Reading never changes anything: transcripts are opened read-only.

## Notes

- Transcripts live at `~/.claude/projects/<folder>/<session-id>.jsonl`. `claude --resume` only finds a session from the folder it was started in; the script reads that folder from the transcript.
- Desktop-app sessions work: the new turn appears in the app's view of that chat. A chat open on screen at that moment may not show it until reopened.
- In `-p` mode Claude cannot ask for permission, so tool calls that need approval are denied. Treat a send as a question Claude answers in text, not a way to make it edit files.
- Each send uses the user's Claude usage.
