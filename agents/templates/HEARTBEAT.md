# <agent-name> Heartbeat

## On wake (every 30min)
1. List all Today-tagged tickets
2. First 30s: BATCH comment each Today ticket with `🔄 CYCLE HH:MM — status: [working|blocked|waiting|done-pending-verify|deferred]`
3. Focus ticket declaration
4. Work
5. Final 5m: close-out comment on focus ticket
6. Update tags (In-Progress / Done / Blocked)

## Violations (count as incomplete)
- Skipping batch step
- Done without file path / commit / URL
- Same copy-paste heartbeat text
- Silence without Blocker declaration
