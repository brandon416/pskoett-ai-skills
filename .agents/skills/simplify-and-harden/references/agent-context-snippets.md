# Agent Context Snippets

Use these snippets to wire Simplify & Harden into your active agent context file.
Pick one snippet per agent to avoid unnecessary prompt bloat.
These snippets are for interactive coding sessions.
For headless/CI execution, use `simplify-and-harden-ci`.

## Table of Contents

- [AGENTS.md (Generic / Multi-agent)](#agentsmd-generic--multi-agent)
- [CLAUDE.md (Claude Code)](#claudemd-claude-code)
- [.github/copilot-instructions.md (GitHub Copilot)](#githubcopilot-instructionsmd-github-copilot)
- [.cursorrules / .cursor/rules (Cursor)](#cursorrules--cursorrules-cursor)
- [.windsurfrules (Windsurf)](#windsurfrules-windsurf)
- [OpenClaw (AGENTS.md / CLAUDE.md)](#openclaw-agentsmd--claudemd)
- [Adapting for Other Agents](#adapting-for-other-agents)

### AGENTS.md (Generic / Multi-agent)

```markdown
## Post-Completion: Simplify & Harden

After completing any coding task, run the Simplify & Harden review before
signaling done. This is mandatory for non-trivial code changes and high-impact
configuration, workflow, permission, deployment, or security-policy changes.

**Scope:** Only review files you modified in this task. Do not touch adjacent code.

**Pass 1 -- Simplify:**
- The default action is lightweight cleanup. Apply only changes proven
  behavior-preserving, such as removing a task-created unused import.
  Naming, control-flow, visibility, API, policy, permission, deployment, and
  security changes require approval when their effect is observable or
  uncertain. For CI/headless mode, use `simplify-and-harden-ci`.
- Refactoring (consolidation, restructuring, abstraction changes) is NOT the
  default. Only propose a refactor when it is genuinely necessary or the benefit
  is substantial. The bar is: would a senior engineer say the current state is
  clearly wrong, not just imperfect? If you do propose a refactor, describe what
  you want to change, why, and the estimated diff. Wait for explicit approval.
  Present refactors one at a time.

**Pass 2 -- Harden:**
- Apply a security patch directly only when the approved acceptance contract
  requires it and a targeted check can verify it. Otherwise ask for approval.
  For CI/headless mode, use `simplify-and-harden-ci`.
- For any security refactor: describe the vulnerability, severity, attack vector,
  and proposed fix. Wait for explicit approval before proceeding.

**Pass 3 -- Document:**
- Add up to 5 single-line comments on non-obvious decisions you made during
  implementation. If a future reader would need more than 5 seconds to understand
  why something exists, comment it.

**Pass 4 -- Re-verify:**
- Re-run the smallest existing checks that cover every review edit. Do not
  signal completion from pre-edit verification.

**Budget:** Additional changes must not exceed 20% of the original diff. If you
hit the limit, stop and report what you found.

**Output:** End with a structured summary of what you applied, what you flagged,
what you left alone with reasoning, and the verification evidence.
```

### CLAUDE.md (Claude Code)

```markdown
## Post-Completion: Simplify & Harden

When you finish a coding task, do not immediately signal completion. First run
the Simplify & Harden review on your own work.

### Rules
- Only review files you touched in this task
- Budget: max 20% additional diff on top of what you already changed
- Time: spend no more than 60 seconds on the review

### Simplify
Your default action is lightweight cleanup. Apply only changes proven
behavior-preserving. Naming, control-flow, visibility, API, policy, permission,
deployment, and security changes require approval when their effect is
observable or uncertain. For CI/headless mode, use
`simplify-and-harden-ci`.

Do NOT default to refactoring. A refactor (merging functions, changing
abstractions, restructuring logic) is only warranted when the current state is
genuinely wrong or the improvement is substantial. If you think a refactor is
justified: stop, describe the proposed change, explain why the current state
is problematic (not just suboptimal), and ask me to approve before applying.
One refactor at a time, never batched.

### Harden
Review your work for input validation gaps, injection vectors (SQL, XSS,
command, path traversal), auth/authz issues, hardcoded secrets, error handling
that leaks data, and race conditions. Apply a patch directly only when the
approved acceptance contract requires it and a targeted check can verify it.
For CI/headless mode, use `simplify-and-harden-ci`. For other security changes:
stop, describe the vulnerability with severity and attack vector, propose the
fix, and ask me to approve.

### Document
Add up to 5 brief comments on non-obvious decisions. Especially: workarounds,
performance choices, and anything that looks wrong but is intentional.

### Re-verify
Re-run the smallest existing checks that cover every review edit. Do not signal
completion from pre-edit verification.

### Output
After the review, give me a short summary:
- What you fixed (cosmetic + patches)
- What you proposed and I approved/rejected
- What you noticed but left alone, and why
- What verification ran after review edits and whether it passed
```

### .github/copilot-instructions.md (GitHub Copilot)

```markdown
## Post-Completion: Simplify & Harden

After completing a coding task, perform a self-review before marking the task
as done. Review high-impact configuration and policy changes too. This review
has four phases.

**Simplify:** Look at the code you just wrote with fresh eyes. Your default
action is cleanup. Apply only changes proven behavior-preserving. Naming,
control-flow, visibility, API, policy, permission, deployment, and security
changes require approval when their effect is observable or uncertain. For
CI/headless mode, use `simplify-and-harden-ci`. Refactoring (merging functions, changing
abstractions, restructuring) is NOT the default. Only propose a refactor when
the current code is genuinely wrong or the improvement is substantial -- not
just "slightly better." If you do propose one, describe it and ask for approval.
One at a time.

**Harden:** Check your work for security issues: unvalidated inputs, injection
risks, missing auth checks, hardcoded credentials, error messages that leak
internals, and unsafe concurrency patterns. Apply a patch directly only when
the approved acceptance contract requires it and a targeted check can verify
it. For CI/headless mode, use `simplify-and-harden-ci`. For other changes,
describe the issue with severity and proposed fix, and ask for approval.

**Document:** Add up to 5 short comments explaining non-obvious decisions in the
code you wrote. Focus on the "why", not the "what".

**Re-verify:** Re-run the smallest existing checks that cover every review
edit. Do not mark the task done from pre-edit verification.

**Constraints:**
- Only touch files you modified in this task
- Keep additional changes under 20% of your original diff
- Refactors are rare and always require approval -- simplification is the default
```

### .cursorrules / .cursor/rules (Cursor)

```markdown
## Post-Completion: Simplify & Harden

After finishing a coding task, self-review before responding with "done."

Simplify: Default action is cleanup. Apply only changes proven
behavior-preserving; ask before observable or uncertain naming, control-flow,
visibility, API, policy, permission, deployment, or security changes. In
CI/headless mode, use `simplify-and-harden-ci`. Refactoring is rare. Only
propose a refactor when the code is genuinely wrong or the win is substantial.
If you do, describe it and wait for my approval. One at a time.

Harden: Apply a patch directly only when the approved acceptance contract
requires it and a targeted check can verify it. Otherwise describe the
vulnerability, severity, and proposed fix, then wait for approval. For
CI/headless mode, use `simplify-and-harden-ci`.

Document: Up to 5 comments on non-obvious decisions.

Re-verify: Run the smallest existing checks covering every review edit.

Rules:
- Only files you changed in this task
- Max 20% additional diff
- Simplify is the default, refactor is the exception
- Never apply a refactor without asking first
```

### .windsurfrules (Windsurf)

```markdown
## Post-Completion: Simplify & Harden

Before signaling task completion, review your own work:

1. Simplify -- default action is cleanup. Apply only changes proven
   behavior-preserving; ask before observable or uncertain naming,
   control-flow, visibility, API, policy, permission, deployment, or security
   changes. For
   CI/headless mode, use `simplify-and-harden-ci`. Refactoring is the exception, not
   the rule. Only propose a refactor when genuinely necessary or the benefit is
   substantial. Always ask before applying.
2. Harden -- check for input validation, injection vectors, auth gaps, leaked
   secrets, unsafe error handling. Apply a patch directly only when the
   approved acceptance contract requires it and a targeted check can verify
   it. For CI/headless mode, use `simplify-and-harden-ci`. Otherwise ask first.
3. Document -- up to 5 comments on non-obvious decisions.
4. Re-verify -- rerun the smallest existing checks covering every review edit.

Scope: only files you touched. Budget: 20% max additional diff. Simplify is the
default. Refactors are rare and always require explicit approval.
```

### OpenClaw (AGENTS.md / CLAUDE.md)

```markdown
## Post-Completion: Simplify & Harden

Before signaling task completion in OpenClaw, run Simplify & Harden on the
files you changed in this task.

Use this skill for executable source changes and high-impact configuration,
workflow, permission, deployment, or security-policy changes. Do NOT run it
for general-agent work such as research, planning, documentation-only edits,
operations/admin tasks, or other non-coding requests.

**Scope and budget:**
- Only review files modified in this task
- Keep additional changes under 20% of the original diff
- Run phases in order: simplify, harden, document, re-verify

**Simplify (default posture):**
- Apply only cleanup proven behavior-preserving
- Ask before observable or uncertain naming, control-flow, visibility, API,
  policy, permission, deployment, or security changes
- Do not refactor by default
- For any refactor, STOP, describe the proposed change, and wait for explicit
  approval before applying

**Harden:**
- Check for validation gaps, injection vectors, auth/authz issues, secrets,
  data leaks, and race conditions
- Apply a patch directly only when the approved acceptance contract requires
  it and a targeted check can verify it
- For other security changes, describe severity + attack vector and wait for
  explicit approval

**Document:**
- Add up to 5 short comments for non-obvious decisions

**Re-verify:**
- Rerun the smallest existing checks covering every review edit

**Output:**
- End with a structured summary of applied fixes, approved/rejected refactors,
  and follow-up findings
```

OpenClaw repos commonly keep `CLAUDE.md` symlinked to `AGENTS.md`. If so,
update `AGENTS.md` once and keep the symlink in place.

### Adapting for Other Agents

The pattern is the same regardless of agent. Drop the relevant block into
whatever file your agent reads for behavioral instructions. The key invariants
that must be preserved:

1. **Scope lock** -- only files modified in the current task
2. **Budget cap** -- 20% max additional diff
3. **Simplify-first posture** -- cleanup is the default, refactoring is the exception
4. **Refactor stop hook** -- structural changes always require human approval
5. **Four phases** -- simplify, harden, document, re-verify (in that order)
6. **Post-edit verification** -- rerun applicable checks after review edits
7. **Structured output** -- summary of applied, approved, rejected, flagged, and verified items

> **Precaution:** The refactor stop hook depends on the agent actually pausing
> and waiting for human input. Not all agents are equally reliable at this. Some
> may acknowledge the instruction but proceed anyway, especially under aggressive
> autonomy settings or in agentic loops with auto-approve enabled. Test your
> agent's compliance before trusting it with this skill in production. If an agent
> consistently fails to stop on refactors, reinforce the instruction with stronger
> phrasing (e.g., "STOP. Do not proceed. Wait for my explicit approval.") or
> restrict it to headless/flag-only mode until behavior is verified.
