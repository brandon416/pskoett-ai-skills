#!/bin/bash
# Context Surfing Handoff Checker Hook
# Triggers on SessionStart to check for pending handoff files
# If found, reminds the agent to load the handoff before starting new work

set -e

HANDOFF_DIR=".context-surfing"

# Skip if no handoff directory exists
if [ ! -d "$HANDOFF_DIR" ]; then
  exit 0
fi

# Find non-empty handoff files without an adjacent .consumed marker.
HANDOFF_FILES=""
while IFS= read -r handoff; do
  if [ ! -e "${handoff}.consumed" ]; then
    HANDOFF_FILES="${HANDOFF_FILES}${handoff}"$'\n'
  fi
done < <(find "$HANDOFF_DIR" -maxdepth 1 -type f -name "handoff-*.md" -size +0c -print 2>/dev/null | sort)
HANDOFF_FILES=${HANDOFF_FILES%$'\n'}

if [ -z "$HANDOFF_FILES" ]; then
  exit 0
fi

# Count handoff files
COUNT=$(echo "$HANDOFF_FILES" | wc -l | tr -d ' ')

cat << EOF
<context-surfing-handoff>
Found ${COUNT} pending handoff file(s) from a previous context-surfing session:

$(echo "$HANDOFF_FILES" | while read -r f; do echo "- $f"; done)

Before starting new work, you MUST:
1. Read the relevant handoff completely
2. Reuse its approved plan and intent frame when they remain valid
3. Run plan-interview only for unresolved requirements or material scope changes
4. After successful re-entry, run: touch '<handoff-path>.consumed'

Do not ignore pending handoff files — they contain session state from a previous context exit.
</context-surfing-handoff>
EOF
