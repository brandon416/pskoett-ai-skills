# Agent Activation and Hooks

Checked against the sources below on 2026-10-17. Hooks are advisory reminders:
the agent decides whether to load the skill and write a learning. These scripts
do not write logs, modify tool results, or guarantee learning capture.

## Contents

- [Requirements and paths](#requirements-and-paths)
- [Claude Code](#claude-code)
- [Codex CLI](#codex-cli)
- [GitHub Copilot CLI and cloud agent](#github-copilot-cli-and-cloud-agent)
- [Amp](#amp)
- [Verification and troubleshooting](#verification-and-troubleshooting)
- [Sources](#sources)

## Requirements and Paths

`activator.sh` needs Bash. `error-detector.sh` needs Bash and **Python 3**; it uses
one JSON parser, not a jq fallback. Install dependencies in the environment where
the agent runs. The shell examples below target Linux/macOS or a compatible Bash
environment; they are not native Windows PowerShell scripts.

With explicit project-scoped installation (see [installation.md](installation.md)):

| Agent | Skill directory |
|-------|-----------------|
| Claude Code | `.claude/skills/self-improvement/` |
| Codex, Copilot, Amp | `.agents/skills/self-improvement/` |
| This repository's canonical source | `skills/self-improvement/` |

Check the actual installed location. User installs and other installers may use
different paths. Quote script paths containing spaces. Merge the examples into
existing settings rather than overwriting unrelated hooks.

## Claude Code

Add to `.claude/settings.json` for a project install:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "\"${CLAUDE_PROJECT_DIR}/.claude/skills/self-improvement/scripts/activator.sh\""
      }]
    }],
    "PostToolUseFailure": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "\"${CLAUDE_PROJECT_DIR}/.claude/skills/self-improvement/scripts/error-detector.sh\" claude-code"
      }]
    }]
  }
}
```

- `UserPromptSubmit` adds the activator's plain stdout to model context. It does
  not support a tool-name matcher or produce a visible chat message.
- `PostToolUse` is the success event. Use **`PostToolUseFailure`** for failed Bash
  calls, whose stdin includes `error`, `tool_name`, and `hook_event_name`.
- The detector returns `hookSpecificOutput.additionalContext` with
  `hookEventName: PostToolUseFailure`, exit 0. It ignores user interruptions and
  non-shell tools. Pre-execution permission denials are not covered by this event.
- For user-wide setup, use `~/.claude/settings.json` and the actual absolute or
  home-anchored script path. Interactive settings-file hooks wait for workspace
  trust; non-interactive/SDK sessions have different trust behavior.
- The native Claude plugin's skill-scoped hooks are generated from
  `assets/claude-hooks.json`, using `CLAUDE_PLUGIN_ROOT`. They activate when the
  skill is loaded. Do not also install duplicate settings-file hooks. The JSON
  asset is not auto-registered by portable Agent Skills clients.

## Codex CLI

Hooks are enabled by default in the current release. If explicitly configuring
them, use `[features] hooks = true` in `config.toml`; `codex_hooks` is a deprecated
alias. Review and trust hook definitions through `/hooks`. Project config also
requires project trust. Changing a trusted definition requires review again.

Use `<repo>/.codex/hooks.json` (or `~/.codex/hooks.json` with an appropriate path):

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "\"$(git rev-parse --show-toplevel)/.agents/skills/self-improvement/scripts/activator.sh\""
      }]
    }]
  }
}
```

Codex adds this plain stdout as developer context. Commands run from the session
working directory, so the example resolves the Git root; outside Git, use an
absolute path. Codex also supports inline `[hooks]` config and Windows-specific
commands, but these Bash scripts still need a compatible environment.

**Do not register this detector on Codex `PostToolUse`.** In release 0.163.0,
unified-exec shell commands match `Bash`, but their hook `tool_response` contains
only output text, without exit status. Silent exit 0 and exit 7 are indistinguishable.
Running commands defer the hook until completion, potentially via `write_stdin`.
Words such as `Error:` are not proof of failure. Use the prompt reminder and
`AGENTS.md` guidance; do not claim reliable automatic failure detection from this
payload. Recheck the release contract before adding it in a future version.

## GitHub Copilot CLI and Cloud Agent

For reminders, keep this in `.github/copilot-instructions.md`:

```markdown
After relevant corrections, discoveries, or unexpected failures, use the
self-improvement skill to evaluate what belongs in .learnings/. Use self-healing
for active recovery when available. Do not duplicate heal entries or save secrets.
```

For failure-specific guidance, create `.github/hooks/self-improvement.json`:

```json
{
  "version": 1,
  "hooks": {
    "postToolUseFailure": [{
      "type": "command",
      "bash": "\"./.agents/skills/self-improvement/scripts/error-detector.sh\" github-copilot",
      "cwd": "."
    }]
  }
}
```

- The camelCase failure payload includes `toolName` and `error`. The detector
  handles shell tools and also accepts the PascalCase event's snake_case payload.
- For this **failure event**, exit **2** with plain stdout appends recovery
  guidance to the failure shown to the model. The detector deliberately uses that
  contract. Do not wrap it in a command that swallows or changes its exit status.
- Successful `postToolUse` hooks can inject **top-level** `additionalContext` JSON
  or modify a result. That differs from Claude's nested envelope. We do not
  register a success hook or change results. Command-hook output from
  `userPromptSubmitted` is ignored, so do not wire `activator.sh` to that event.
- CLI supports personal `~/.copilot/hooks/*.json` (or `$COPILOT_HOME/hooks/`) and
  additional settings/plugin sources. Use actual installed paths for personal
  hooks. Cloud agent reads repository `.github/hooks/*.json`; commit the skill
  and config so its Linux sandbox has them. Personal installs do not transfer.
- Cloud sandbox files are ephemeral. A reminder is not a persisted audit log.
  These examples use `bash`, not a Windows `powershell` hook command.

## Amp

Amp discovers `.agents/skills/self-improvement` and loads its instructions on
demand. Claude/Copilot hook JSON does not enable an Amp lifecycle plugin. See
[amp-setup.md](amp-setup.md) for native per-turn reminders and verification.

## Verification and Troubleshooting

Run from this repository root:

```bash
python3 scripts/test-self-improvement-hooks.py
bash -n skills/self-improvement/scripts/error-detector.sh
```

The regression tests check failure guidance, success/interrupt controls,
agent-specific output and exit codes, and absence of file writes. These are
standalone contract tests, **not live agent lifecycle tests**.

After installing hooks, start a session, review trust prompts, submit a prompt,
then ask the agent to run a harmless failing shell command such as `exit 7` in a
disposable directory. Inspect the host's hook/debug output and model context.
For Codex, verify only the prompt reminder, not automatic failure detection.
Context injection need not appear as a visible transcript message.

If nothing fires: check the event name, trusted config, actual quoted script path,
executable permission, Bash/Python availability, and whether the plugin skill has
been loaded. Disable by removing the relevant registration, not by adding comments
to JSON. Keep failure data out of logs unless explicitly needed and redacted.

## Sources

- [Claude hooks](https://code.claude.com/docs/en/hooks)
- [Codex release behavior](https://learn.chatgpt.com/docs/hooks)
- [Codex 0.163.0 output-only hook payload](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/src/tools/context.rs#L432-L445)
- [Copilot hook events and output](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Amp skills](https://ampcode.com/docs/customize/skills)
- [Amp plugins](https://ampcode.com/docs/customize/plugins)
