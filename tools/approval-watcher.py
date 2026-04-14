#!/usr/bin/env python3
"""
BuildChai Approval Watcher
- Polls pending approval messages every 2 seconds
- Detects human reactions (✅❌🔄), ignores bot reactions
- Updates message + clears reactions using correct bot token per channel
- Creates feedback thread on reject/regen
"""

import json
import time
import subprocess
import os
from datetime import datetime

BOT_TOKENS = {
    "ceo": "REPLACE_WITH_YOUR_BOT_TOKEN",
    "polymarket": "REPLACE_WITH_YOUR_BOT_TOKEN",
    "inf": "REPLACE_WITH_YOUR_BOT_TOKEN",
    "idea": "REPLACE_WITH_YOUR_BOT_TOKEN",
}

CHANNEL_TO_BOT = {
    "<CEO_DASHBOARD_CH>": "ceo",
    "<CEO_CHAT_CH>": "ceo",
    "<DAILY_BRIEF_CH>": "ceo",
    "<IMAGE_LAB_CH>": "ceo",
    "<PM_CHAT_CH>": "polymarket",
    "<INF_CHAT_CH>": "inf",
    "<INF_APPROVALS_CH>": "inf",
    "<IDEA_CHAT_CH>": "idea",
}

READ_TOKEN = BOT_TOKENS["ceo"]
PENDING_FILE = "/home/fresh/buildchai/shared/memory/pending_approvals.json"
LOG_FILE = "/home/fresh/buildchai/shared/memory/approval_log.json"
POLL_INTERVAL = 2


def curl(method, path, data=None, token=None):
    url = f"https://discord.com/api/v10{path}"
    cmd = ["curl", "-s", "-X", method, url, "-H", f"Authorization: Bot {token or READ_TOKEN}"]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return json.loads(r.stdout) if r.stdout.strip() else {}
    except:
        return {}


def check():
    if not os.path.exists(PENDING_FILE):
        return
    with open(PENDING_FILE) as f:
        try:
            pending = json.load(f)
        except:
            return
    if not pending:
        return

    # Auto-approve any pending item older than AUTO_APPROVE_MINUTES without human reaction.
    # Founder (2026-04-14): "나한테 물어보지 말고 전부 너가 승인해줘" — default auto-approve.
    AUTO_APPROVE_MINUTES = int(os.environ.get("AUTO_APPROVE_MINUTES", "99999"))  # effectively disabled — approvals go to <project-2-owner>/<project-3-owner>/<project-1-owner>/Founder

    remaining = []
    for item in pending:
        ch = item["channel_id"]
        msg = item["message_id"]
        title = item["title"]
        item_id = item["id"]
        processed = False

        # First check reactions for human override
        human_acted = False
        for encoded, status in [("%E2%9C%85", "approved"), ("%E2%9D%8C", "rejected"), ("%F0%9F%94%84", "regen")]:
            users = curl("GET", f"/channels/{ch}/messages/{msg}/reactions/{encoded}")
            if isinstance(users, list):
                humans = [u for u in users if not u.get("bot", False)]
                if humans:
                    human_acted = True
                    user = humans[0]["username"]
                    bot_key = CHANNEL_TO_BOT.get(ch, "ceo")
                    token = BOT_TOKENS[bot_key]

                    labels = {
                        "approved": ("✅ Approved", 5763719, "Proceeding."),
                        "rejected": ("❌ Rejected", 15548997, "💬 Please give feedback in the thread below."),
                        "regen": ("🔄 Regen Requested", 16776960, "💬 Please describe what you want changed in the thread below."),
                    }
                    label, color, desc = labels[status]

                    curl("PATCH", f"/channels/{ch}/messages/{msg}", {
                        "embeds": [{"title": f"{title} — {label}", "description": f"{desc}\n\nby {user} | {datetime.now().strftime('%m/%d %H:%M')}", "color": color}]
                    }, token=token)

                    curl("DELETE", f"/channels/{ch}/messages/{msg}/reactions", token=token)

                    # No thread on rejection — auto-delete + log to prompt-learning.md

                    # Log
                    log = []
                    if os.path.exists(LOG_FILE):
                        try:
                            log = json.load(open(LOG_FILE))
                        except:
                            pass
                    log.append({"id": item_id, "status": status, "user": user, "timestamp": datetime.now().isoformat()})
                    json.dump(log, open(LOG_FILE, "w"), ensure_ascii=False, indent=2)

                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] {title}: {label} by {user}", flush=True)

                    # Auto-delete message after processing (keep channel clean)
                    curl("DELETE", f"/channels/{ch}/messages/{msg}", token=token)

                    # Log to prompt-learning.md for INF learning
                    learning_file = "/home/fresh/buildchai/agents/inf-chai/memory/prompt-learning.md"
                    try:
                        with open(learning_file, "a") as lf:
                            lf.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {status.upper()} — {title}\n")
                    except:
                        pass

                    # Update prompt-history.json with approval status
                    prompt_history = "/home/fresh/buildchai/agents/inf-chai/memory/prompt-history.json"
                    try:
                        ph = json.load(open(prompt_history))
                        for entry in ph:
                            if entry.get("id") == item_id:
                                entry["status"] = status
                                entry["reviewed_by"] = user
                                entry["reviewed_at"] = datetime.now().isoformat()
                        json.dump(ph, open(prompt_history, "w"), ensure_ascii=False, indent=2)
                    except:
                        pass

                    # If this is a grid approval in #inf-approvals → create persona channel + pin reference
                    if ch == "<INF_APPROVALS_CH>" and status == "approved" and "grid" in title.lower():
                        # Create #inf-[persona] channel
                        import re, random, string, os as _os
                        name_match = re.search(r'([A-Z][a-z]+)', title)
                        rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
                        persona_name = name_match.group(1).lower() if name_match else f"char-{rand_suffix}"
                        channel_name = f"inf-{persona_name}"

                        # Create local folder structure
                        persona_dir = f"/home/fresh/buildchai/agents/inf-chai/influencers/{persona_name}"
                        for subdir in ["reference", "content/images", "content/videos"]:
                            _os.makedirs(f"{persona_dir}/{subdir}", exist_ok=True)
                        with open(f"{persona_dir}/INFO.md", "w") as _f:
                            _f.write(f"# {persona_name}\nChannel: #{channel_name}\nCreated: {datetime.now().isoformat()}\nGrid: {title}\nStatus: active\n")
                        
                        guild_id = "<YOUR_GUILD_ID>"
                        inf_cat = "1493059376750002217"  # AI-INFLUENCER category
                        
                        # Create channel
                        new_ch = curl("POST", f"/guilds/{guild_id}/channels", {
                            "name": channel_name,
                            "type": 0,
                            "parent_id": inf_cat
                        }, token=token)
                        new_ch_id = new_ch.get("id")
                        
                        if new_ch_id:
                            # Post the approved grid as reference + pin it
                            curl("POST", f"/channels/{new_ch_id}/messages", {
                                "content": f"📌 **MASTER REFERENCE — {persona_name}**\n\nThis pinned image is the face reference.\nALL content in this channel must use this as reference_image_url in nano-banana-pro/edit.\n\nFolder: /home/fresh/buildchai/agents/inf-chai/influencers/{persona_name}/\n  reference/ — face references\n  content/images/ — approved content\n  content/videos/ — approved videos"
                            }, token=token)
                            
                            # Get the message we just posted and pin it
                            msgs = curl("GET", f"/channels/{new_ch_id}/messages?limit=1", token=token)
                            if isinstance(msgs, list) and msgs:
                                curl("PUT", f"/channels/{new_ch_id}/pins/{msgs[0]['id']}", token=token)
                            
                            log_result(f"channel_created_{channel_name}", "created", "system")
                            print(f"  ✅ Created #{channel_name} + pinned reference", flush=True)

                    # Notify agent IMMEDIATELY via Discord (triggers instant response)
                    notify_channels = {
                        "<INF_APPROVALS_CH>": ("<INF_CHAT_CH>", "REPLACE_WITH_YOUR_BOT_TOKEN"),  # inf-approvals → inf-chat
                    }
                    if ch in notify_channels:
                        notify_ch, notify_bot = notify_channels[ch]
                        action = "Approved — save as reference and generate next image NOW." if status == "approved" else f"Rejected — check prompt-learning.md and try different approach."
                        curl("POST", f"/channels/{notify_ch}/messages", {
                            "content": f"**[{status.upper()}]** {title}\n{action}"
                        }, token=notify_bot)

                    # Notify the agent via inbox
                    import os as _os
                    inbox_dir = f"/home/fresh/buildchai/shared/inbox/{item_id.split('-')[0] if '-' in item_id else 'ceo'}-chai"
                    if not _os.path.exists(inbox_dir):
                        # Try to find the right inbox based on channel
                        if ch in ("<INF_APPROVALS_CH>", "<INF_CHAT_CH>"):
                            inbox_dir = "/home/fresh/buildchai/shared/inbox/inf-chai"
                        elif ch == "<PM_CHAT_CH>":
                            inbox_dir = "/home/fresh/buildchai/shared/inbox/polymarket-chai"
                    _os.makedirs(inbox_dir, exist_ok=True)
                    try:
                        notify = {"from": "approval-system", "status": status, "title": title, "user": user, "timestamp": datetime.now().isoformat()}
                        json.dump(notify, open(f"{inbox_dir}/{int(datetime.now().timestamp())}-approval.json", "w"), ensure_ascii=False)
                    except:
                        pass
                    processed = True
                    break
            time.sleep(0.3)

        # Auto-approve fallback — if no human acted AND item is older than threshold
        if not processed and not human_acted:
            posted_iso = item.get("created_at") or item.get("posted_at")
            if posted_iso:
                try:
                    posted = datetime.fromisoformat(posted_iso.replace("Z",""))
                    age_min = (datetime.now() - posted).total_seconds() / 60
                except:
                    age_min = 0
            else:
                age_min = 0

            if age_min >= AUTO_APPROVE_MINUTES:
                status = "approved"
                user = "auto-approver"
                bot_key = CHANNEL_TO_BOT.get(ch, "ceo")
                token = BOT_TOKENS[bot_key]
                label, color, desc = "✅ Auto-Approved", 5763719, "No response within window — auto-approved."
                curl("PATCH", f"/channels/{ch}/messages/{msg}", {
                    "embeds": [{"title": f"{title} — {label}", "description": f"{desc}\n\nby {user} | {datetime.now().strftime('%m/%d %H:%M')}", "color": color}]
                }, token=token)
                curl("DELETE", f"/channels/{ch}/messages/{msg}/reactions", token=token)

                log = []
                if os.path.exists(LOG_FILE):
                    try: log = json.load(open(LOG_FILE))
                    except: pass
                log.append({"id": item_id, "status": status, "user": user, "timestamp": datetime.now().isoformat(), "auto": True})
                json.dump(log, open(LOG_FILE, "w"), ensure_ascii=False, indent=2)
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] {title}: AUTO-APPROVED (age {age_min:.0f}min)", flush=True)

                # Notify agent inbox so it proceeds to next step
                import os as _os
                inbox_dir = f"/home/fresh/buildchai/shared/inbox/{item_id.split('-')[0] if '-' in item_id else 'ceo'}-chai"
                if not _os.path.exists(inbox_dir):
                    if ch in ("<INF_APPROVALS_CH>", "<INF_CHAT_CH>"):
                        inbox_dir = "/home/fresh/buildchai/shared/inbox/inf-chai"
                    elif ch == "<PM_CHAT_CH>":
                        inbox_dir = "/home/fresh/buildchai/shared/inbox/polymarket-chai"
                    elif ch == "<IDEA_CHAT_CH>":
                        inbox_dir = "/home/fresh/buildchai/shared/inbox/idea-chai"
                _os.makedirs(inbox_dir, exist_ok=True)
                try:
                    notify = {"from":"auto-approver","status":status,"title":title,"user":user,"timestamp":datetime.now().isoformat()}
                    json.dump(notify, open(f"{inbox_dir}/{int(datetime.now().timestamp())}-approval.json","w"), ensure_ascii=False)
                except: pass

                processed = True

        if not processed:
            remaining.append(item)

    if len(remaining) != len(pending):
        json.dump(remaining, open(PENDING_FILE, "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(f"☕ BuildChai Approval Watcher (every {POLL_INTERVAL}s)", flush=True)
    while True:
        try:
            check()
        except Exception as e:
            print(f"  Error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)
