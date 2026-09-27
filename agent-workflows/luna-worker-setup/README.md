# Luna Worker Setup

This resource configures Codex to delegate bounded, independently reviewable work to a dedicated luna_worker subagent running GPT-6 Luna with Max reasoning. The parent agent keeps task framing, authority, integration, evidence review, and final acceptance.

The setup has four layers:

1. `AGENTS.md` explains when to delegate and which decisions stay with the parent.
2. `agents/luna-worker.toml` defines the worker as a bounded GPT-6 Luna Max role.
3. `config.toml` enables subagents, caps per-session concurrency at three, and sets the model and reasoning defaults used by the setup.
4. `skills/delegate-bounded-work/SKILL.md` gives the parent a task packet and review process.

The bundled `setup-luna-worker` skill guides inspection, preview, application, and verification. The installer itself supports user or project scope and previews changes by default.

## Requirements

- Codex with subagent support and access to `gpt-6-luna` at `max` reasoning.
- Python 3.11 or newer.
- Write access to the selected Codex home or project folder.

Model availability, configuration fields, and Codex behavior can change. Check the [current subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [plugin documentation](https://developers.openai.com/plugins/build/plugins) before applying the setup.

## Quick Start

Read [INSTALL.md](INSTALL.md) for the full bootstrap, scope choices, backups, rollback, and runtime check.

The public resource URL is:

<https://github.com/willkinsey/ai-for-knowledge-workers-resources/tree/main/agent-workflows/luna-worker-setup>

From a local clone:

    cd agent-workflows/luna-worker-setup
    python3 scripts/install.py --scope user

That command previews the user-scope changes and writes nothing. Review the preview, then apply with:

    python3 scripts/install.py --scope user --apply
    python3 scripts/verify.py --scope user

User scope is the recommended starting point for a reusable personal setup. Project scope is available when the rules and defaults should apply only to one repository.

## Files Written by the Installer

Choose one scope. The installer writes these four files within that target:

| Scope | Managed files |
| --- | --- |
| User | `<Codex home>/config.toml`; `<Codex home>/agents/luna-worker.toml`; `<Codex home>/AGENTS.md`; `<Codex home>/skills/delegate-bounded-work/SKILL.md` |
| Project | `<project>/.codex/config.toml`; `<project>/.codex/agents/luna-worker.toml`; `<project>/AGENTS.md`; `<project>/.codex/skills/delegate-bounded-work/SKILL.md` |

For user scope, Codex home defaults to `CODEX_HOME` when set, or `~/.codex`. Project scope requires the project root as `--target`. The preview identifies the selected paths before any write. Existing files that will change receive sibling timestamped backups before the installer writes them.

The user-scope `[agents]` settings are defaults across subagents using that Codex home. The dedicated `luna_worker` role pins GPT-6 Luna Max; an explicitly configured role or direct launch can override general defaults.

## Why Max

This setup deliberately preserves the requested GPT-6 Luna Max configuration. In the Artificial Analysis model leaderboard checked on 2026-09-25, Max was the highest-scoring Luna reasoning setting shown in its Intelligence Index. That is dated third-party benchmark evidence, not an OpenAI recommendation or a guarantee of quality, speed, or value on a particular task. The [official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) describes High as a general starting point and Max or xhigh for especially demanding reasoning; this kit keeps Max because that is the selected configuration.

## Limits

- File verification checks the saved setup. It cannot confirm that a live Codex session loaded it, that the account can use GPT-6 Luna Max, or that a worker will perform a task well.
- After applying, start a fresh Codex session and use a harmless bounded task to confirm the runtime-selected model and effort. Stop and report a model or effort availability problem; do not switch silently to another model.
- The setup does not grant permissions, install credentials, or authorize the worker to exceed the parent task's scope.

## Rights

The repository's [MIT License](../../LICENSE) covers the written instructions and scripts in this resource. No brand, screenshot, slide, or other media assets are included. See the repository's [content rights notice](../../CONTENT-RIGHTS.md).
