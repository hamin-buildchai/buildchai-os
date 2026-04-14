#!/bin/bash
# Hourly review dump — collects last 1h messages from all agent+owner channels.
# Runs at minute 00 each hour. Output: /tmp/hourly-review/HH.md
# Claude Code reads this file and teaches agents in its next wake.

set -euo pipefail

DIR="/tmp/hourly-review"
mkdir -p "$DIR"
HOUR=$(TZ=America/Denver date +%H)
DATE=$(TZ=America/Denver date +%Y-%m-%d)
OUT="$DIR/${DATE}-${HOUR}.md"
TOKEN="REPLACE_WITH_YOUR_BOT_TOKEN"

CHANNELS=(
  "ceo-chat|<CEO_CHAT_CH>"
  "ceo-dashboard|<CEO_DASHBOARD_CH>"
  "daily-brief|<DAILY_BRIEF_CH>"
  "polymarket-chat|<PM_CHAT_CH>"
  "inf-chat|<INF_CHAT_CH>"
  "inf-approvals|<INF_APPROVALS_CH>"
  "idea-chat|<IDEA_CHAT_CH>"
  "ceo-polymarket-discuss|<CEO_PM_DISCUSS_CH>"
  "ceo-inf-discuss|<CEO_INF_DISCUSS_CH>"
  "ceo-idea-discuss|<CEO_IDEA_DISCUSS_CH>"
)

SINCE_TS_MS=$(($(date +%s) * 1000 - 3600 * 1000))  # 1 hour ago in ms (approx)

{
  echo "# Hourly Review — ${DATE} ${HOUR}:00 MDT"
  echo ""
  for entry in "${CHANNELS[@]}"; do
    name="${entry%%|*}"
    ch="${entry##*|}"
    echo "## #${name}"
    curl -s -H "Authorization: Bot ${TOKEN}" \
      "https://discord.com/api/v10/channels/${ch}/messages?limit=50" \
      | python3 -c "
import json, sys, datetime
msgs = json.load(sys.stdin)
if not isinstance(msgs, list):
    print('  (channel inaccessible)')
    sys.exit()
cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1, minutes=5)
recent = [m for m in msgs if datetime.datetime.fromisoformat(m['timestamp'].replace('Z','+00:00')) > cutoff]
if not recent:
    print('  (no new messages)')
    sys.exit()
for m in reversed(recent[:30]):
    auth = m.get('author',{}).get('username','?')
    is_bot = m.get('author',{}).get('bot', False)
    tag = '[bot]' if is_bot else '[human]'
    ts = m['timestamp'][11:19]
    content = m.get('content','').replace('\n', ' / ')[:300]
    print(f'- {ts} {tag} {auth}: {content}')
" 2>/dev/null || echo "  (error fetching)"
    echo ""
  done
  echo "## Recent file changes (last 1h)"
  find /home/fresh/buildchai -newer /tmp/hourly-review-marker -type f 2>/dev/null | head -15
  touch /tmp/hourly-review-marker
} > "$OUT"

ls -la "$OUT"
