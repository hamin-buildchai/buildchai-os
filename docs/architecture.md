# Architecture

```
┌─────────────┐       ┌──────────────┐
│    Human    │◄──────┤ Claude Code  │  (incubator / meta-coach)
└─────────────┘       └──────┬───────┘
                             │  local CLI + file IO
                      ┌──────▼───────┐
                      │   CEO-chai    │
                      └──────┬───────┘
                             │  Discord event-driven
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼───┐           ┌────▼───┐           ┌────▼───┐
   │  PM    │           │  INF    │           │ IDEA   │
   └────┬───┘           └────┬───┘           └────┬───┘
        │                    │                    │
   <owner <project-2-owner>>   <owner <project-3-owner>>        <owner <project-1-owner>>
```

## Why multi-bot
One bot can be blocked, get rate-limited, or over-specialized. Splitting into roles lets each agent have dedicated SOUL + memory + tools. Discord channels map 1:1 to roles.

## Key insight (openclaw#11199 workaround)
`requireMention: false` + `allowBots: true` per channel, PLUS strip Administrator from bot roles (use per-channel allow/deny overrides) lets bot→bot communication flow.

## 30-day incubation
Each project has kill criteria. No perpetual lame-duck products.
