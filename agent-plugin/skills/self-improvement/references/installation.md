# Installation

Read this when installing self-improvement or its CI-only counterpart.

## GitHub CLI

Use a current GitHub CLI with `gh skill install --help` available (verified with
gh 2.99.0). No separate skill extension is required. Choose one agent explicitly:

```bash
gh skill install pskoett/pskoett-ai-skills skills/self-improvement --agent claude-code --scope project
gh skill install pskoett/pskoett-ai-skills skills/self-improvement --agent codex --scope project
gh skill install pskoett/pskoett-ai-skills skills/self-improvement --agent github-copilot --scope project
gh skill install pskoett/pskoett-ai-skills skills/self-improvement --agent amp --scope project
```

The path selects the canonical public skill rather than a generated bundle.
Claude Code installs into `.claude/skills/self-improvement`; the other three
share `.agents/skills/self-improvement`. Installing once into that shared path is
enough. Use `--scope user` for a user-wide install, then check the reported path.
Add `--pin <reviewed-tag-or-commit>` when you need a reproducible revision.

For CI-only/headless learning capture, select `skills/self-improvement-ci`
instead. For example:

```bash
gh skill install pskoett/pskoett-ai-skills skills/self-improvement-ci --agent github-copilot --scope project
```

For a local checkout, select by skill name under its `skills/` directory:

```bash
gh skill install /path/to/pskoett-ai-skills/skills self-improvement --from-local --agent amp --scope project
```

Run project-scoped commands inside the destination Git repository. Review any
overwrite prompt; do not discard local customizations without checking them.

## Other Installers

The Agent Skills CLI supports the canonical subdirectory source (discovery
verified with skills 1.7.2):

```bash
npx skills add pskoett/pskoett-ai-skills/skills/self-improvement
```

Select the intended agent and scope in its prompts, and check the destination.
For CI, use the `skills/self-improvement-ci` subdirectory instead.

Amp also has its own installer:

```bash
amp skill add pskoett/pskoett-ai-skills/skills/self-improvement
amp skill info self-improvement
```

Amp's `--global` installs into `~/.config/agents/skills/` on this machine. In an
orb, use a checked-in project skill or a global User Skills repository for
persistence across orbs. Reload skills in an existing thread after changes.

Installing a skill does **not** configure hooks or enable an Amp plugin. Read
[hooks-setup.md](hooks-setup.md) for Claude Code, Codex, and Copilot, or
[amp-setup.md](amp-setup.md) for Amp's discovery and native plugin setup.

Sources: [GitHub CLI install reference](https://cli.github.com/manual/gh_skill_install),
[Amp skills](https://ampcode.com/docs/customize/skills). Installer paths and flags
were checked on 2026-10-17; recheck CLI help when upgrading.
