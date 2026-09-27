---
name: setup-luna-worker
description: Install, update, or verify the Luna Worker Setup in Codex user or project scope.
---

# Set Up the Luna Worker

Use this skill only for the Luna Worker Setup resource.

1. Read the resource's `INSTALL.md` and inspect the selected Codex home or project root, including existing target files and permissions.
2. Preview the selected scope with `python3 scripts/install.py` using the documented flags. The default is a dry run.
3. Apply changes only when the user requested setup or an update. Preserve the selected GPT-6 Luna Max choice.
4. Run `python3 scripts/verify.py` with the same scope and target after applying or when asked to verify.
5. Report the scope, exact paths inspected or changed, backup paths created, and verifier result. Distinguish saved-file verification from a live runtime check.

If target files cannot be read or written, stop and report the permission or access blocker. Do not claim that setup or verification succeeded without the corresponding evidence.

If GPT-6 Luna or Max is unavailable, report the limitation and stop. Never silently fall back to another model or reasoning level.
