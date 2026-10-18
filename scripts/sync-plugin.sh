#!/bin/bash
# Syncs canonical skills into plugin distributions and managed .agents copies.
#
# scripts/skill-distributions.json owns membership and native registration.
# Skill-owned assets/claude-hooks.json overrides configured hooks. Portable and
# managed .agents copies contain canonical metadata and runtime resources, not evals.
# Unlisted .agents skills are left alone. Generated files are never inputs.
#
# Delegates to scripts/sync_plugin.py (requires python3 + PyYAML).
#
# Usage: ./scripts/sync-plugin.sh [skill-name ...]
#   No args: sync all configured skills.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$REPO_ROOT/scripts/sync_plugin.py" "$@"
