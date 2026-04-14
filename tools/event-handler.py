#!/usr/bin/env python3
"""
BuildChai 이벤트 핸들러
- 리액션 즉시 감지 → 승인/거절/재생성 처리
- 스레드 자동 생성 (거절/재생성 시)
- 폴링 없음, Discord Gateway 이벤트 기반
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime

import discord

BOT_TOKEN = "REPLACE_WITH_YOUR_BOT_TOKEN"
PENDING_FILE = "/home/fresh/buildchai/shared/memory/pending_approvals.json"
LOG_FILE = "/home/fresh/buildchai/shared/memory/approval_log.json"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)


def load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE) as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_pending(items):
    with open(PENDING_FILE, "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def log_result(item_id, status, user):
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            try:
                log = json.load(f)
            except:
                log = []
    log.append({
        "id": item_id,
        "status": status,
        "user": user,
        "timestamp": datetime.now().isoformat()
    })
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


@client.event
async def on_ready():
    print(f"☕ BuildChai 이벤트 핸들러 시작: {client.user}")
    print(f"  감시 중: 리액션 이벤트")


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # 봇 자신의 리액션 무시
    if payload.user_id == client.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in ("✅", "❌", "🔄"):
        return

    msg_id = str(payload.message_id)
    channel_id = str(payload.channel_id)

    # pending 목록에서 확인
    pending = load_pending()
    target = None
    for item in pending:
        if item["message_id"] == msg_id:
            target = item
            break

    if not target:
        return

    # 유저 정보
    guild = client.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    username = member.display_name if member else str(payload.user_id)

    # 상태 결정
    status_map = {
        "✅": ("approved", "✅ 승인됨", 0x57F287),
        "❌": ("rejected", "❌ 거절됨", 0xED4245),
        "🔄": ("regen", "🔄 재생성 요청", 0xFEE75C)
    }
    status, label, color = status_map[emoji]

    # 메시지 업데이트
    channel = client.get_channel(payload.channel_id)
    if channel:
        try:
            message = await channel.fetch_message(payload.message_id)

            # 임베드 업데이트
            embed = discord.Embed(
                title=f"{target['title']} — {label}",
                description=f"처리: {datetime.now().strftime('%m/%d %H:%M')} by {username}",
                color=color
            )
            await message.edit(embeds=[embed])

            # 리액션 전부 제거
            await message.clear_reactions()

            # 거절/재생성이면 피드백 스레드 생성
            if status in ("rejected", "regen"):
                thread_name = f"💬 {target['title']} 피드백"
                thread = await message.create_thread(
                    name=thread_name[:100],
                    auto_archive_duration=1440
                )
                prompt = "거절 이유를 적어주세요." if status == "rejected" else "원하는 방향을 적어주세요."
                await thread.send(
                    f"📝 **{prompt}**\n"
                    f"여기에 피드백을 남기면 에이전트가 반영합니다.\n\n"
                    f"예시:\n- \"색깔이 너무 진해\"\n- \"더 미니멀하게\"\n- \"배경을 흰색으로\""
                )

            print(f"  {target['title']}: {emoji} by {username}")

        except Exception as e:
            print(f"  오류: {e}")

    # 로그 + pending에서 제거
    log_result(target["id"], status, username)
    pending = [p for p in pending if p["message_id"] != msg_id]
    save_pending(pending)


if __name__ == "__main__":
    client.run(BOT_TOKEN, log_handler=None)
