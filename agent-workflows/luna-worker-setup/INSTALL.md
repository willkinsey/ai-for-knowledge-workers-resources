# Install the Luna Worker Setup

This guide is the bootstrap for the public [Luna Worker Setup resource](https://github.com/willkinsey/ai-for-knowledge-workers-resources/tree/main/agent-workflows/luna-worker-setup). It previews and applies local Codex files for a dedicated `luna_worker` at GPT-6 Luna Max, then verifies the saved files.

## Requirements and Scope

- Python 3.11 or newer.
- A Codex installation with subagent support and access to GPT-6 Luna at `max` reasoning.
- Write permission for the Codex home or project folder you select.

User scope is recommended for a reusable setup. It writes to the Codex home, so its configuration and delegation rules can affect work across projects using that home. Its `[agents]` defaults apply across subagents using that home; the dedicated `luna_worker` role pins GPT-6 Luna Max, while explicitly configured roles or direct launches can override general defaults. Project scope keeps the setup associated with one project and writes that project's root `AGENTS.md`.

The installer defaults to user scope. For user scope, its target defaults to `CODEX_HOME` when set, or `~/.codex`. For project scope, pass the project root with `--target`.

## 1. Get the Resource

Clone the public repository and enter the resource folder:

    git clone https://github.com/willkinsey/ai-for-knowledge-workers-resources.git
    cd ai-for-knowledge-workers-resources/agent-workflows/luna-worker-setup

Check that `python3 --version` reports Python 3.11 or newer. Before applying, open the [current subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [plugin documentation](https://developers.openai.com/plugins/build/plugins). Confirm the model name, reasoning option, and configuration fields are still supported in your Codex version. The installer does not fetch or validate remote documentation.

## 2. Preview the User-Scope Changes

The installer is a dry run unless `--apply` is supplied:

    python3 scripts/install.py --scope user

Read the preview and confirm the resolved target paths. It should identify these managed files:

- `<Codex home>/config.toml`
- `<Codex home>/agents/luna-worker.toml`
- `<Codex home>/AGENTS.md`
- `<Codex home>/skills/delegate-bounded-work/SKILL.md`

You can set a different Codex home explicitly with `--target <codex-home>`. The dry run makes no target changes.

## 3. Apply the Setup

Apply the reviewed user-scope plan:

    python3 scripts/install.py --scope user --apply

For a project-only setup, preview first, then apply to the same project root:

    python3 scripts/install.py --scope project --target <project-root>
    python3 scripts/install.py --scope project --target <project-root> --apply

Project scope manages:

- `<project-root>/.codex/config.toml`
- `<project-root>/.codex/agents/luna-worker.toml`
- `<project-root>/AGENTS.md`
- `<project-root>/.codex/skills/delegate-bounded-work/SKILL.md`

Before writing, the installer makes a sibling backup of each existing target file it will change. Backup names include `.bak-` and a UTC timestamp. It writes changes atomically and stops if it cannot safely resolve an existing configuration.

## 4. Verify the Saved Files

Run the read-only verifier with the same scope and target:

    python3 scripts/verify.py --scope user

For project scope, use `python3 scripts/verify.py --scope project --target <project-root>`. The verifier checks saved files only; it does not start a worker or prove model access.

## 5. Check the Live Runtime

Start a fresh Codex session so it reads the saved configuration. Give it a harmless, bounded task and explicitly request `luna_worker` or GPT-6 Luna with Max reasoning. Confirm the child session's model and effort from the runtime's available settings or task details. If the profile, model, or effort is unavailable, stop and report that limitation. Do not silently substitute another model or reasoning level.

This smoke test is separate from file verification. A passing verifier does not guarantee account access, live configuration pickup, or task quality.

## Roll Back

For each changed file that existed before installation, restore the matching sibling `.bak-<UTC timestamp>` copy after reviewing that it is the correct backup. Re-run the verifier or inspect the target paths to confirm the state you intended.

The installer does not create backups for files that did not exist before setup. If you roll back those newly created files, first confirm they have no later edits or uses, then remove only the specific files created by this installation.

## Installer Commands

    python3 scripts/install.py [--scope user|project] [--target PATH] [--apply]
    python3 scripts/verify.py [--scope user|project] [--target PATH]

--scope user is the default. Project scope requires --target. Omit --apply to preview without writing.
