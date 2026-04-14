#!/usr/bin/env python3
"""
BuildChai Discussion Runner
CEO ↔ PM — 매 라운드 Claude Opus 교차검증
Opus 실패 시 Codex만으로 진행 (실패 표시)
"""

import subprocess
import json
import sys
import time
from datetime import datetime

CEO_BOT = "REPLACE_WITH_YOUR_BOT_TOKEN"
PM_BOTS = {
    "polymarket-chai": "REPLACE_WITH_YOUR_BOT_TOKEN",
    "inf-chai": "REPLACE_WITH_YOUR_BOT_TOKEN",
    "idea-chai": "REPLACE_WITH_YOUR_BOT_TOKEN",
}

def post_discord(channel_id, bot_token, content):
    cmd = ["curl", "-s", "-X", "POST",
           f"https://discord.com/api/v10/channels/{channel_id}/messages",
           "-H", f"Authorization: Bot {bot_token}",
           "-H", "Content-Type: application/json",
           "-d", json.dumps({"content": content[:2000]})]
    subprocess.run(cmd, capture_output=True, timeout=10)

def run_agent(agent_id, message, max_attempts=3):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = subprocess.run(
                ["/home/fresh/.npm-global/bin/openclaw", "agent", "--agent", agent_id, "--message", message],
                capture_output=True, text=True, timeout=300
            )
            lines = result.stdout.strip().split("\n")
            response = "\n".join(l for l in lines
                if not l.startswith("[") and not l.startswith("gateway")
                and not l.startswith("Error") and "synced openai" not in l
                and "agents/auth" not in l and l.strip())
            if response:
                return response
            return result.stdout.strip()[-500:] or f"(empty response {agent_id})"
        except subprocess.TimeoutExpired as e:
            last_err = e
            if attempt < max_attempts:
                wait = 5 * (3 ** (attempt - 1))  # 5s, 15s, 45s
                time.sleep(wait)
                continue
    # 3 retries exhausted — return sentinel so caller continues
    return f"⚠️ {agent_id} timeout x{max_attempts}"

def run_claude(message):
    try:
        result = subprocess.run(
            ["claude", "-p", message, "--model", "opus",
             "--dangerously-skip-permissions", "--output-format", "text"],
            capture_output=True, text=True, timeout=120
        )
        lines = result.stdout.strip().split("\n")
        response = "\n".join(l for l in lines if not l.startswith("Warning") and l.strip())
        return response if response else None
    except:
        return None

def run_discussion(pm_id, channel_id, rounds=20):
    pm_bot = PM_BOTS.get(pm_id, CEO_BOT)
    log = []

    # CEO opens
    ceo_msg = run_agent("ceo-chai",
        f"Start discussion with {pm_id}. Read memory/pre-discussion-data.md and memory/tomorrow-direction.md. Key numbers. 3 sentences max.")
    post_discord(channel_id, CEO_BOT, f"**ceo-chai:**\n{ceo_msg}")
    log.append(f"CEO: {ceo_msg}")
    context = ceo_msg

    for i in range(rounds):
        time.sleep(2)

        # PM responds
        pm_msg = run_agent(pm_id,
            f"ceo-chai said: {context}\n\nRespond with status, data, plan. 3 sentences max.")
        post_discord(channel_id, pm_bot, f"**{pm_id}:**\n{pm_msg}")
        log.append(f"{pm_id}: {pm_msg}")

        time.sleep(1)

        # Claude 교차검증 — 매 라운드
        claude_review = run_claude(
            f"CEO and {pm_id} are discussing. CEO said: {context}\n{pm_id} replied: {pm_msg}\n\n"
            f"What's wrong or missing? 1-2 sentences only. If nothing wrong, say 'OK'.")

        if claude_review:
            # CEO가 Codex + Claude 양쪽 반영해서 답변
            ceo_msg = run_agent("ceo-chai",
                f"{pm_id} said: {pm_msg}\n\nClaude Opus review: {claude_review}\n\n"
                f"Incorporate Claude's feedback. Respond with next direction. 3 sentences max.")
            dual_label = f"🧠 opus: {claude_review[:100]}"
            post_discord(channel_id, CEO_BOT, f"{dual_label}\n\n**ceo-chai:**\n{ceo_msg}")
            log.append(f"OPUS: {claude_review}")
        else:
            # Opus 실패 — Codex만
            ceo_msg = run_agent("ceo-chai",
                f"{pm_id} said: {pm_msg}\n\nRespond. 3 sentences max.")
            post_discord(channel_id, CEO_BOT, f"⚠️ *opus unavailable*\n\n**ceo-chai:**\n{ceo_msg}")

        log.append(f"CEO: {ceo_msg}")
        context = ceo_msg
        # Per-round flush so we don't lose progress on timeout
        try:
            log_file = f"/home/fresh/buildchai/shared/memory/discussion-{pm_id}-{datetime.now().strftime('%Y-%m-%d')}.md"
            with open(log_file, "w") as _f:
                _f.write(f"# {pm_id} Discussion — {datetime.now().strftime('%Y-%m-%d %H:%M')} (in-progress)\n\n")
                for entry in log:
                    _f.write(f"{entry}\n\n")
        except Exception: pass
        time.sleep(1)

    # Final TODO
    claude_final = run_claude(
        f"Discussion ending. Last 4 exchanges:\n" + "\n".join(log[-8:]) +
        f"\n\nFinal check: is the TODO clear and correct? 2 sentences.")
    
    ceo_final = run_agent("ceo-chai",
        f"Discussion ending. Claude final: {claude_final or 'unavailable'}\n\n"
        f"Confirm final TODO for {pm_id}. List specific tickets.")
    
    final_msg = ""
    if claude_final:
        final_msg += f"🧠 **opus final:** {claude_final}\n\n"
    else:
        final_msg += "⚠️ *opus unavailable for final check*\n\n"
    final_msg += f"**ceo-chai TODO:**\n{ceo_final}"
    post_discord(channel_id, CEO_BOT, final_msg)

    # Save log
    log_file = f"/home/fresh/buildchai/shared/memory/discussion-{pm_id}-{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(log_file, "w") as f:
        f.write(f"# {pm_id} Discussion — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        for entry in log:
            f.write(f"{entry}\n\n")

if __name__ == "__main__":
    pm = sys.argv[1] if len(sys.argv) > 1 else "polymarket-chai"
    channel = sys.argv[2] if len(sys.argv) > 2 else "<CEO_PM_DISCUSS_CH>"
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    run_discussion(pm, channel, rounds)
