#!/bin/bash
# Failure-event reminder. Requires Bash and Python 3.
# Usage: error-detector.sh [claude-code|github-copilot]
# Register only on PostToolUseFailure (Claude) / postToolUseFailure (Copilot).
# Codex 0.163.0 does not expose a reliable exit status in Bash hook stdin.

set -e

# One parser avoids jq/Python fallback differences. stdin remains the event JSON.
exec python3 -c '
import json
import sys

agent = sys.argv[1]
if agent not in ("claude-code", "github-copilot"):
    print("Expected claude-code or github-copilot", file=sys.stderr)
    sys.exit(1)
try:
    event = json.load(sys.stdin)
except (ValueError, OSError):
    print("Expected hook JSON on stdin", file=sys.stderr)
    sys.exit(1)
if not isinstance(event, dict):
    print("Expected a hook JSON object", file=sys.stderr)
    sys.exit(1)

tool = event.get("tool_name") or event.get("toolName")
if not isinstance(tool, str) or tool.lower() not in ("bash", "shell", "powershell"):
    sys.exit(0)
if event.get("is_interrupt") is True:
    sys.exit(0)
if agent == "claude-code" and event.get("hook_event_name") != "PostToolUseFailure":
    sys.exit(0)
if agent == "github-copilot" and event.get("hook_event_name") not in (None, "PostToolUseFailure"):
    sys.exit(0)
if not isinstance(event.get("error"), str):
    sys.exit(0)

# Do not copy untrusted or potentially secret command output into the reminder.
reminder = """<error-detected>
A shell tool failed. If this is unexpected and needs active recovery, use
self-healing when available: diagnose, fix, verify, then record the heal.
For a past failure not already captured as a heal, consider a concise entry in
.learnings/ERRORS.md using self-improvement. Do not duplicate HEAL entries,
log expected failures, or include secrets.
</error-detected>"""

if agent == "github-copilot":
    # Copilot failure hooks append stdout as recovery guidance on exit 2.
    print(reminder)
    sys.exit(2)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PostToolUseFailure",
    "additionalContext": reminder,
}}))
' "${1:-claude-code}"
