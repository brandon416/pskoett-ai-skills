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
