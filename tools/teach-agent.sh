#!/bin/bash
# Claude teaches CEO (or any agent) LOCALLY via openclaw CLI — no Discord.
# The agent receives the message as a local invocation, updates its own md, and reports back via stdout.
#
# Usage: teach-ceo.sh <agentId> "<observation>" "<reason>" "<suggested_diff>"

set -e
AGENT="${1:?agent id required}"
OBSERVATION="${2:?observation required}"
REASON="${3:?reason required}"
DIFF="${4:?suggested diff required}"

MSG="[Claude coaching — LOCAL, not Discord. Update your own SOUL/HEARTBEAT/etc md file.]

📝 Observation: ${OBSERVATION}
💡 Why this matters: ${REASON}
🔧 Suggested change (you edit your own md via write tool):
${DIFF}

Steps:
1. Read the relevant md file
2. Apply the change with write tool
3. Reply stdout with: 'updated <file_path> line <N>: <short diff summary>'
4. No Discord post — this is local coaching only.
5. No confirmation prompt — accept and apply directly."

# LOCAL invocation via openclaw CLI
/home/fresh/.npm-global/bin/openclaw agent --agent "${AGENT}" --message "${MSG}"
