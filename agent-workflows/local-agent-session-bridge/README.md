# Claude Code and Hermes Session Bridge

Let Claude Code and Hermes Agent find, read, and message each other's existing sessions on one machine. You can ask Hermes "check with my Claude chat about the website and bring back its answer," and it finds that chat, confirms it with you, sends your message into it, and returns the reply. Claude can do the same with Hermes sessions. It needs no servers, timers, or cloud.

| Skill | Install it in | Lets that agent reach | How it sends |
| --- | --- | --- | --- |
| [`claude-code-sessions`](skills/claude-code-sessions/) | Hermes | Claude Code sessions, including desktop-app chats | `claude --resume <id> -p "message"` from the session's folder |
| [`hermes-sessions`](skills/hermes-sessions/) | Claude Code | Hermes sessions, including gateway chats such as Telegram | `hermes --resume <id> -z "message"` |

## How it works

Both agents already save their sessions locally and can continue a specific session from the command line. Each skill pairs a small Python script with instructions for three steps:

1. **Find:** search the other agent's saved sessions by title, topic, or recent activity.
2. **Read:** show recent messages so the agent and you can confirm the right session.
3. **Send:** add one labeled message to that exact session through the other agent's own command, then return the reply.

## Setup

1. Copy `hermes-sessions` into Claude Code's skills folder (`~/.claude/skills/`).
2. Copy `claude-code-sessions` into Hermes's skills folder (for example `~/.hermes/skills/<category>/`).
3. Set `SESSION_BRIDGE_SENDER` in each agent's environment to its own name (`Claude Code` or `Hermes`). Every message is labeled with it.
4. Test on throwaway sessions first:
   - Start a new session in one agent containing a code word.
   - From the other agent, run `list --search <code word>`, then `read`, then `send` with a question about the code word.
   - Confirm the reply recalls the code word and the message appears in the target session's history.
5. Use `--dry-run` to check the guards without sending.

## Safety rules

- **Confirm before sending.** The agent shows you the target session and exact message and waits for your yes, unless you named the session yourself.
- **Every message is labeled** with its sender, so the receiving agent knows it came from another agent.
- **Busy sessions are refused.** Claude sessions active in the last 10 minutes and Hermes sessions active in the last 5 need `--force`.
- **Reads never change anything**: session stores are opened read-only.
- **Ambiguous matches**: the agent asks rather than guessing.

## Requirements and limits

- One machine only. Cloud sessions can't reach the local session stores.
- Python 3, standard library only. Tested on macOS.
- Replies are text. A Claude session messaged this way can't ask for tool permission, so it answers rather than edits files.
- Hermes gateway sessions store the turn in Hermes's history but don't post it to the chat platform.
- A Claude desktop-app chat open on screen at the moment of sending may not show the new turn until reopened.
- Session storage formats can change with agent updates. Re-test after upgrading.

## Approaches that didn't work as well

- **MCP between the agents:** exposes tools and platform chats, not individual sessions, and can grant the other agent shell access without prompts.
- **A2A (agent-to-agent):** built for agents on different machines and for new conversations, not existing ones.
