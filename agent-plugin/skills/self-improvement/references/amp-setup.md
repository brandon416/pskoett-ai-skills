# Amp Setup

## Skill Discovery Is Not a Hook

Install using [installation.md](installation.md), then run:

```bash
amp skill info self-improvement
```

In this repository, Amp discovers `.agents/skills/self-improvement/SKILL.md`.
The public `skills/` directory is the distribution source, not the active installed
copy. Keep the full installed directory synchronized, including references and
scripts. Use Amp's `reload_skills` tool after edits, then ask it to load
`self-improvement` to verify the instructions and resources are available.

The skill description and `AGENTS.md` guide when the model should load it.
That is instruction-driven activation, not an automatic shell failure detector.
Claude frontmatter hooks and Copilot hook JSON do not register Amp events.

## Optional Per-Turn Plugin

A native Amp plugin can return a hidden context message from `agent.start`,
which fires when a user submits an initial prompt or reply. It should remind the
agent to evaluate relevant corrections and discoveries before finishing, route
active failures to self-healing when available, and avoid duplicate or sensitive
records. The skill remains a separate installation.

Use a single root `self-improvement.ts` file in a **User Plugins** repository for
cross-machine use. Discover the writable repository with:

```bash
amp plugins repositories
amp plugins show-docs
```

Follow the printed `amp clone` command and place the file at the clone root.
Project-specific plugins can instead live in `.amp/plugins/`; user-local
`~/.config/amp/plugins/` plugins only persist on that machine. Choose one location
to avoid duplicate reminders. Global plugins do not become active until committed
and pushed with the user's approval. New threads load the published version;
existing threads need `reload_plugins`.

The handler uses this API shape:

```typescript
import type { PluginAPI } from '@ampcode/plugin'

export const description = 'Adds a per-turn self-improvement reminder.'

export default function (amp: PluginAPI) {
  amp.on('agent.start', () => ({
    message: {
      content: 'Before finishing, evaluate relevant learnings with the self-improvement skill when available. Use self-healing for active recovery. Avoid duplicate entries and secrets; do not force a log when there is no useful learning.',
      display: false,
    },
  }))
}
```

Return the message from the event handler. Do not append thread messages, start
another agent turn, or alter tool results. The plugin itself needs no filesystem,
shell, network, or logging access. It cannot guarantee that the model records a
learning, and it must not silently install a missing skill or promote guidance.

## Verification

From the plugin clone, smoke-test loading without publishing:

```bash
amp plugins exec ./self-improvement.ts agent.start --data '{"thread":{"id":"T-00000000-0000-0000-0000-000000000000"},"message":"Review a correction","id":"test"}'
```

Do not treat exit 0 alone as proof that the handler ran. The checked Amp CLI
loaded a probe plugin but did not invoke its `agent.start` handler through this
command. Separately test the registered handler's return value: one `message`
with the reminder and `display: false`, with no follow-up turn or tool changes.
After publication, reload plugins and inspect `amp plugins list` and
`amp skill info self-improvement`. Test a relevant correction in a disposable
project and review the resulting learning rather than assuming hidden context
was followed. A normal prompt with no learning should not create a file.

Sources checked 2026-10-17: [Amp skills](https://ampcode.com/docs/customize/skills),
[Amp plugins](https://ampcode.com/docs/customize/plugins), and the installed
`amp plugins show-docs` API. Recheck that API before changing event handling.
