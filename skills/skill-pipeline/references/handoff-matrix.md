# Handoff Matrix

Artifact flow, signal routing, precedence rules, and budget constraints across the skill pipeline.

## Artifact Flow

| Producing Skill | Artifact | Consuming Skill(s) |
|----------------|----------|-------------------|
| `plan-interview` | `docs/plans/plan-NNN-<slug>.md` | `intent-framed-agent` (context), `context-surfing` (wave anchor), optional `control-session-orchestrator` work-unit breakdown |
| `intent-framed-agent` | Intent Frame (in-session) | `session-context` (retrieval task and scope), then `context-surfing` (wave anchor), handoff files on exit |
| `session-context` | Cited prior-session brief or explicit no-match/unavailable status (in-session) | `intent-framed-agent` (refine approach; resolve material conflicts without treating history as authority) |
| `context-surfing` | `.context-surfing/handoff-[slug]-[timestamp].md` | Next session (resume), `plan-interview` (replanning input) |
| `simplify-and-harden` | `learning_loop.candidates` (YAML) | `self-improvement` (pattern logging) |
| `simplify-and-harden-ci` | PR comment + check run + YAML findings | `self-improvement-ci` (recurrence tracking) |
| `self-healing` | `.learnings/HEALS.md` (HEAL entries with verification proof) + `.learnings/heals/<HEAL-ID>/` (lazy artifacts: scripts, patches, notes) | `pre-flight-check` (surfaces prior heals by Pattern-Key / Active-Context); `learning-aggregator` (cross-session recurrence); `self-improvement` (Handoff blocks at Recurrence ≥ 3) |
| `self-improvement` | `.learnings/LEARNINGS.md`, `.learnings/ERRORS.md`, `.learnings/FEATURE_REQUESTS.md` | Promotion targets: `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` |

## Signal Routing

| Signal | Source | Action |
|--------|--------|--------|
| Task classified | `skill-pipeline` | Activate appropriate skills |
| Plan approved by user | `plan-interview` | Auto-start execution; a faithful intent frame reuses this approval |
| Planning-to-execution transition | User cues ("go ahead", "implement this") | Activate `intent-framed-agent` |
| Initial intent frame emitted | `intent-framed-agent` | Invoke `session-context` once when available, before finalizing the approach |
| Prior-session retrieval complete or unavailable | `session-context` | Refine the same frame and continue; ask only about material unresolved conflicts |
| Large/Long-running task or explicit context-pressure signal | `skill-pipeline` or user | Activate `context-surfing` |
| Task completion (exit code 0, PR ready) | Implementation | Activate `simplify-and-harden` for non-trivial executable changes or high-impact configuration/policy changes |
| Intent Resolution emitted | `intent-framed-agent` | Signal `simplify-and-harden` readiness |
| Drift exit (strong signal) | `context-surfing` | Stop execution, write handoff file, notify user |
| Weak drift signal | `context-surfing` | One local re-anchor, one cold-context check, then escalate or exit |
| Intent Check fired | `intent-framed-agent` | Pause, evaluate scope, user decides |
| Command / test / build / lint failure | Any execution step (esp. `verify-gate`) | Activate `self-healing` (diagnose → patch → verify → file HEAL) |
| Missing capability / helper needed | Implementation | Activate `self-healing` (write the helper, save under `.learnings/heals/<HEAL-ID>/`, file HEAL) |
| Heal Handoff block emitted | `self-healing` (at Recurrence ≥ 3) | Activate `self-improvement` for promotion to memory file or new skill |
| Error, correction, knowledge gap | Any skill | Activate `self-improvement` |
| Learning promotion threshold met | `self-improvement` | Update CLAUDE.md / AGENTS.md / copilot-instructions.md |

## Precedence Rules

1. **context-surfing exit > intent-framed-agent Intent Check** — If both fire simultaneously, resolve context degradation first. Degraded context makes scope checks unreliable.
2. **simplify-and-harden re-entry guard** — The skill does not run twice on the same task. No re-entry loops.
3. **Plan-interview is a human gate** — Never auto-invoke. Recommend when task classifies as Large, but user decides.
4. **Quality gates are non-negotiable:** clean compile, tests pass, observable acceptance criteria hold, and audit-driven edits are re-verified.

## Budget Constraints

| Skill | Constraint | Value |
|-------|-----------|-------|
| `session-context` | Default task-wide retrieval and brief | Two search rounds, three sessions read, roughly 600 tokens; reuse on resume |
| `simplify-and-harden` | Max additional diff | 20% of original diff size |
| `simplify-and-harden` | Max execution time | 60 seconds |
| `simplify-and-harden` | Document pass | Max 5 comments |

## Context File Loading

From `context-surfing`, load only bounded anchors at activation:
- The applicable agent instruction file(s)
- The approved plan or intent artifact, when present
- The user task description
- `README.md` only when project structure or purpose is relevant

Load on demand when relevant:
- Specific `.md` files in `skills/`, `docs/`, or `.learnings/`
- `SKILL.md` files for skills being invoked

## Learning Loop Integration

Pattern keys emitted by code review skills:
- **Simplify:** `simplify.dead_code`, `simplify.naming`, `simplify.control_flow`, `simplify.over_abstraction`
- **Harden:** `harden.input_validation`, `harden.authorization`, `harden.error_handling`, `harden.injection_vectors`, `harden.secrets_exposure`

Promotion threshold: recurrence count >= 3, seen across >= 2 distinct tasks, within 30-day window.
