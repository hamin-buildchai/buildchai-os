# Patterns — what we learned running multi-agent AI on Discord

Each pattern is a problem we hit and how we solved it. Copy the thinking, not the code.

---

## 1. Event-driven over polling

**Problem.** Agents polling a channel every 5 minutes feel dead. Users abandon them.

**Solution.** Discord Gateway WebSocket handled by the agent framework (OpenClaw) reacts in ~20 seconds. Heartbeat polling (every 30 min) is only for idle checks — never the primary reaction path.

**Gotcha.** The event loop can still fail silently if the gateway drops without reconnect-with-resume. Monitor for "Gateway reconnect scheduled" storms; they indicate instability.

---

## 2. N-agent one Discord server (the openclaw #11199 trap)

**Problem.** Running N agents as separate Discord bot users on one server — the orchestration framework filters messages from "other bots" which includes your own team's bots. Inter-agent messages never fire.

**Solution.** Three combined settings:
- `requireMention: false` per channel
- `allowBots: true` on each bot account
- Strip `Administrator` from bot roles (Admin overrides per-channel denies)
- Per-channel `deny` overrides when you need to exclude a specific bot from a specific channel

See [`config/openclaw.template.json`](../config/openclaw.template.json).

**Gotcha.** CEO-bot usually has Admin for infra tasks; can't strip. Use **user-level** channel override (`type: 1, id: <bot_user_id>, deny: VIEW_CHANNEL`) for channels that must exclude CEO bot.

---

## 3. Owner-separated approval

**Problem.** If one person (the founder) approves everything, the team bottlenecks. Approval latency = velocity loss.

**Solution.** Each project has its own approver (not the founder). Agent posts approval requests with an `@<project-owner>` mention + `allowed_mentions` to trigger real push notification. The CEO agent is a *second-opinion reviewer*, never the decision-maker.

**Pattern for the post.**
```
<@PROJECT_OWNER_ID> approval request
📊 [one-line evidence]
📝 [recommendation]
[✅ / ❌ / 🔄 buttons]
```

With `allowed_mentions: {"users":["PROJECT_OWNER_ID"]}` — without this, the mention is text-only and no notification fires.

---

## 4. 30-day KPI gate

**Problem.** Side projects accumulate indefinitely. No one pulls the plug.

**Solution.** Every project has a 30-day target (user inflow or revenue). Daily KPI report includes `Day X/30, progress N%`. If Day 30 arrives without signal → kill or pivot. Projects that graduate get spun out into their own repo/process.

Not a new idea, but enforcing it on AI-run projects where "demo works" is tempting forever.

---

## 5. Self-teaching loop (meta-coach)

**Problem.** Hand-editing each agent's SOUL.md every time you spot a behavior issue doesn't scale. Also defeats "agent system" — you're just writing prompts manually.

**Solution.** A Claude Code session (the coach) reads the last hour's conversations across channels, spots issues, and sends a *teaching message* to the offending agent via local openclaw CLI. The agent updates its own SOUL.md using its write tool. Coach verifies by file diff.

**The teaching prompt shape:**
```
📝 Observation: [what happened]
💡 Why this matters: [principle violated]
🔧 Suggested change: [concrete diff to SOUL/HEARTBEAT]
✅ Confirm: reply "updated <file> line <N>: <diff>"
```

**Key rule.** Coach doesn't edit agent md directly. If coach writes the rules, agent never learns.

---

## 6. Multi-step completion (agent's favorite failure mode)

**Problem.** You give the agent a 5-step task ("scan → write file → post to Discord → verify → approve request"). Agent does step 1-2 then says "완료했습니다" (done) and terminates.

Why: conversational-mode training. Agent treats file-write as the main task, Discord-post as optional continuation.

**Solution (partial).**
- Add a rule to SOUL: *"파일 write = partial. Completion requires STEP N verified."*
- Add `STEP 1 / STEP 2 / ...` structure to cron prompts with "termination forbidden until STEP N output captured".
- Verify side-effects existed (Discord message posted, file created) — if not, the task didn't complete regardless of what the agent said.

**Still not 100%.** Agent occasionally ignores the hard rule. Coach checks every hour; re-invokes with stricter wording. This pattern is ongoing.

---

## 7. Batch heartbeat (ticket discipline)

**Problem.** Agents post "working on X" to the chat channel every 30 minutes. Channel noise destroys signal. Users tune out.

**Solution.** First 30 seconds of each heartbeat = batch update **every Today-tagged ticket thread** with a one-line status, not the chat channel:
```
🔄 CYCLE HH:MM — status: [working | blocked | waiting | done-pending-verify | deferred]
```
Chat channel = critical announcements only (approvals, completions with memo/ID-mention). Nothing else.

---

## 8. Shell helpers vs. agent autonomy

**Problem.** Agents trying to use `curl` with complex JSON payloads often hang or error. Tempting to have a shell script just do the Discord post.

**Rule.** If shell writes the message content, you no longer have an agent system — you have a cron system.

**Solution.** Shell provides a **one-arg helper** (`post-discord.sh <channel> <content-stdin>`). Agent decides the content; shell handles escape/API details. Agent autonomy + infra reliability.

---

## 9. Kill criteria for sub-daemons

**Problem.** Polling side-car daemons accumulate. Each new problem tempts a new `*-watcher.py`.

**Rule.** Every polling daemon needs a kill criterion. *"If the framework provides this natively, stop the sidecar."*

We ran an `opus-verifier` polling daemon, then enabled OpenClaw's native `dual-verify` hook — until the hook broke with `missing scope: operator.write`. Bringing the sidecar back was right. If OpenClaw fixes scope later, kill the sidecar again.

Never ship a permanent sidecar "just in case."

---

## 10. Coach is not a fifth agent

**Problem.** Tempting to add a "monitor agent" in Discord that watches other agents.

**Rule.** The coach is **out-of-band** — it's the person (or Claude Code session) running locally, reading logs, teaching each agent separately. Putting the coach into the Discord graph makes it just another chatter. Out-of-band preserves authority.

---

## Non-patterns (things we tried that didn't work)

- **Forcing agents to post heartbeat to chat** — produced noise, now forbidden.
- **Manually editing agent SOUL to "fix" behavior** — agent never internalized it. Use teaching instead.
- **Larger round counts in agent↔agent discussions** (30R, 50R) — after round ~12 they repeat themselves. 20R is the limit.
- **Unified approval for all projects via one person** — bottleneck.

---

More notes will land as we iterate. Issues/discussions welcome.
