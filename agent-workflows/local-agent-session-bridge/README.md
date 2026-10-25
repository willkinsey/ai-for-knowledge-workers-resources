# Local Agent Session Bridge

Let local AI agents find, read, and message each other's existing sessions on one machine. You can ask one agent "check with my Claude chat about the website and bring back its answer," and it finds that chat, confirms it with you, sends your message into it, and returns the reply. It needs no servers, timers, or cloud.

Supported targets:

| Skill | Lets any agent reach | How it sends |
| --- | --- | --- |
| [`claude-code-sessions`](skills/claude-code-sessions/) | Claude Code sessions, including desktop-app chats | `claude --resume <id> -p "message"` from the session's folder |
| [`hermes-sessions`](skills/hermes-sessions/) | Hermes Agent sessions, including gateway chats such as Telegram | `hermes --resume <id> -z "message"` |
| [`codex-desktop-sessions`](skills/codex-desktop-sessions/) | Codex desktop chats | Codex App Server `thread/queue/add`; the desktop app answers in the chat |

## How it works

Every agent already saves its sessions locally and has a way to continue a specific session. Each skill pairs a small Python script with instructions for three steps:

1. **Find:** search the target agent's saved sessions by title, topic, or recent activity.
2. **Read:** show recent messages so the agent and you can confirm the right session.
3. **Send:** add one labeled message to that exact session through the target agent's own tools, then return the reply.

Install the skill for each agent you want to *reach* into the agent that will *do the reaching*. For example, give Claude Code `hermes-sessions`, and give Hermes `claude-code-sessions`, for two-way messaging between them.

## Setup

1. Copy the skill folders you need into the calling agent's skills directory (for example `~/.claude/skills/` for Claude Code, or `~/.hermes/skills/<category>/` for Hermes).
2. Set `SESSION_BRIDGE_SENDER` in the calling agent's environment to its name, for example `Claude Code` or `Hermes`. Every message is labeled with it.
3. Test on throwaway sessions first:
   - Start a new session in the target agent containing a code word.
   - From the calling agent, run `list --search <code word>`, then `read`, then `send` with a question about the code word.
   - Confirm the reply recalls the code word and the message appears in the target session's history.
4. Use `--dry-run` (Claude and Hermes skills) to check guards without sending.

## Safety rules

- **Confirm before sending.** The agent shows you the target session and exact message and waits for your yes, unless you named the session yourself.
- **Every message is labeled** with its sender, so the receiving agent knows it came from another agent.
- **Busy sessions are refused.** Claude and Hermes sessions active in the last 10 or 5 minutes need `--force`. Codex chats that are busy or have queued work are refused.
- **Reads never change anything**: session stores are opened read-only.
- **No duplicate sends** in the Codex skill: each request has a unique ID, and an uncertain delivery is never retried.
- **Ambiguous matches**: the agent asks rather than guessing.

## Requirements and limits

- One machine only. Cloud sessions can't reach the local session stores.
- Python 3 (3.11+ for the Codex skill), standard library only. Tested on macOS.
- Replies are text. A Claude session messaged this way can't ask for tool permission, so it answers rather than edits files.
- Hermes gateway sessions store the turn in Hermes's history but don't post it to the chat platform.
- The Codex skill relies on an experimental App Server queue API and the ChatGPT desktop app's bundled Codex CLI. It refuses to run on an untested Codex version until you set `CODEX_VERIFIED_VERSION` after your own test.
- Session storage formats can change with agent updates. Re-test after upgrading.

## Approaches that didn't work as well

- **MCP between agents:** exposes tools and platform chats, not individual sessions, and can grant another agent shell access without prompts.
- **A2A (agent-to-agent):** built for agents on different machines and for new conversations, not existing ones.
- **A mailbox plus a scheduled check for Codex:** works, but costs a model turn on every check. The App Server queue replaced it.
