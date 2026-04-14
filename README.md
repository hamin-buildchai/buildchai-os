<p align="center">
  <b>BuildChai OS</b> — notes & patterns from running a multi-agent Discord AI workforce
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img src="https://img.shields.io/badge/status-notes-orange">
  <img src="https://img.shields.io/badge/contains-patterns%20%2B%20lessons-blue">
</p>

---

This is not a framework to clone and run. It's what we learned running a multi-agent AI company at [buildchai.com](https://buildchai.com) — patterns, workarounds, and reference code we'd want if we were starting over.

Adapt the ideas, not the config.

## Why this exists

We run N AI agents on one Discord server — a CEO orchestrator plus project owners — each with its own memory, approvals, and 30-day KPI gate. Six weeks of iteration produced a handful of patterns that saved us from rewriting a lot of code. This repo is those patterns.

## What's in here

**Patterns** (core value) — see [`docs/patterns.md`](docs/patterns.md)
- `event-driven-over-polling` — why 20s reaction beats 5-minute cron polling
- `n-agent-one-server` — Discord multi-bot workaround (the openclaw #11199 trap)
- `owner-separated-approval` — why one approver bottlenecks a team
- `30-day-kpi-gate` — lightweight kill criteria for AI side projects
- `self-teaching-loop` — meta-coach (Claude Code) teaches agent to edit its own SOUL
- `multi-step-completion` — how agents skip steps, how to catch it

**Reference code** (adapt, don't copy) — [`tools/`](tools/)
- `approval-watcher.py` — polling loop for pending approvals with human reaction detection
- `event-handler.py` — discord.py Gateway WebSocket (reactions + button interactions)
- `run-discussion.py` — N-round agent↔agent discussion with retry + per-round flush
- `hourly-review-dump.sh` — collect last 1h cross-channel messages for coach review
- `post-discord.sh` — one-liner Discord post helper (handles escape/payload)
- `send-approval-button.sh` — Components v2 button poster
- `teach-agent.sh` — local coaching wrapper (teach the agent to update its own md)

**Starter SOUL/HEARTBEAT templates** — [`agents/templates/`](agents/templates/)

**Architecture notes** — [`docs/architecture.md`](docs/architecture.md)

## Principles

- Agents write their own SOUL/HEARTBEAT — humans don't edit agent markdown directly
- 30-day KPI kill gate. No perpetual lame-duck products
- Event-driven over polling wherever possible
- Shell does infrastructure; agents do judgment
- Per-project approver, never one person for everything

## What we don't provide

- Guild/channel/bot ID values — use your own
- Turnkey "run this script" deployment — patterns assume you understand what you're doing
- Promises of stability — we rewrite things weekly as we learn

## Contributing

Bug reports and pattern discussions welcome. Early and rough — expect breaking changes.

## License

MIT.
