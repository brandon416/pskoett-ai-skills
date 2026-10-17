# Verified runtime recoveries

## [HEAL-20261005-001] isolated-plugin-validation-dependencies

**Logged**: 2026-10-05
**Status**: verified
**Trigger**: env-issue
**Area**: validation
**Priority**: low

### Failure
`./scripts/sync-plugin.sh context-decay` failed with
`ModuleNotFoundError: No module named 'yaml'`. The portable validator also
reported missing `jsonschema` in the orb's default Python environment.

### Diagnosis
The validation scripts need Python packages absent from the default interpreter.

### Fix
Run the existing commands with isolated dependencies:
`uv run --with pyyaml --with jsonschema -- bash -c './scripts/sync-plugin.sh context-decay && python3 scripts/validate-agent-plugin.py'`.

### Verification
The command exited 0: `SYNCED context-decay` and
`Agent Plugins package validation passed: 16 portable skills, 48 portable artifacts, 16 native mirrors, MCP not declared, version 2.6.2.`

On 2026-10-17, the same missing `yaml` dependency blocked self-improvement sync
and its regression checks. Re-ran with
`uv run --with PyYAML==6.0.3 --with jsonschema==4.25.1 -- bash -c './scripts/sync-plugin.sh self-improvement && python3 scripts/test-sync-plugin.py && python3 scripts/validate-agent-plugin.py'`.
Exit 0: `SYNCED self-improvement`, `Portable sync regression checks passed.`,
and package validation passed for 17 portable skills and 17 native mirrors.

### Metadata
- Related Files: scripts/sync_plugin.py, scripts/validate-agent-plugin.py
- Pattern-Key: env.plugin_validation_python_dependencies
- Recurrence-Count: 2
- First-Seen: 2026-10-05
- Last-Seen: 2026-10-17

---

## [HEAL-20261017-001] gh-local-skill-selection

**Logged**: 2026-10-17
**Status**: verified
**Trigger**: tool-failure
**Area**: validation
**Priority**: low

### Failure
The disposable installer probe using gh 2.99.0 with the repository root,
`skills/self-improvement`, and `--from-local` exited 1:
`skill "skills/self-improvement" not found in local directory`.

### Diagnosis
The attempted exact-path selection did not work in this local-install invocation.
Do not assume all remote path-selection behavior applies to `--from-local`.

### Fix
Use the canonical `skills/` directory as the local source and the discovered name:
`gh skill install /home/user/workspace/repo/skills self-improvement --from-local --agent <agent> --scope project`.

### Verification
Re-ran the install in four disposable Git repositories. All exited 0 and created
`SKILL.md`: `.claude/skills/self-improvement/` for `claude-code`, and
`.agents/skills/self-improvement/` for `codex`, `github-copilot`, and `amp`.
Temporary repositories were removed; no active skill installation changed.

### Metadata
- Pattern-Key: cli.gh_local_skill_selection
- Recurrence-Count: 1
- First-Seen: 2026-10-17
- Last-Seen: 2026-10-17

---

## [HEAL-20261017-002] amp-plugin-exec-lifecycle-probe

**Logged**: 2026-10-17
**Status**: abandoned
**Trigger**: tool-failure
**Area**: validation
**Priority**: low

### Failure and Diagnosis
Amp CLI 0.0.1792254886-g14d018 returned exit 0 with no result from
`amp plugins exec <plugin> agent.start --data <fixture>`.
A temporary wrapper wrote a load sentinel but no callback-result sentinel.
The plugin loaded; callback dispatch was not demonstrated. Root cause unknown.
The debug log showed plugin-process shutdown code 130, not a handler exception.

### Fix and Verification
No host fix applied. A separate Bun harness invoked the production handler and
verified one hidden reminder for three prompts, no prompt-text interpolation,
and no other registered event or return action. This verifies the handler
contract only, not Amp lifecycle delivery. Corrected the new Amp setup reference
to state this limitation. Full lifecycle verification remains pending deployment
and a real prompt; do not count CLI exit 0 as proof. Removed temporary probes.

### Metadata
- Pattern-Key: cli.amp_plugin_exec_agent_start
- Recurrence-Count: 1
- First-Seen: 2026-10-17
- Last-Seen: 2026-10-17
