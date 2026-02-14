"""Discord 봇 엔트리포인트"""

import os
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from dotenv import load_dotenv

from claude_client import PropertyAssistant
from formatters import send_long_message

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Rate limiting
rate_limits: dict[int, list[datetime]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))

# 대화 이력 (채널별)
conversation_history: dict[int, list[dict]] = defaultdict(list)
MAX_HISTORY = int(os.environ.get("MAX_CONVERSATION_HISTORY", "10"))

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

assistant = PropertyAssistant()


def check_rate_limit(user_id: int) -> bool:
    """Rate limit 체크 (분당 N회)"""
    now = datetime.now()
    cutoff = now - timedelta(minutes=1)
    rate_limits[user_id] = [t for t in rate_limits[user_id] if t > cutoff]
    if len(rate_limits[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return False
    rate_limits[user_id].append(now)
    return True


@bot.event
async def on_ready():
    """봇 시작 시 MCP 서버 연결"""
    logger.info(f"봇 로그인: {bot.user}")
    mcp_path = os.environ.get("MCP_SERVER_PATH", "./mcp_server/server.py")
    await assistant.connect_mcp(mcp_path)
    logger.info("MCP 서버 연결 완료")


@bot.event
async def on_message(message: discord.Message):
    """메시지 수신 처리"""
    # 봇 자신의 메시지 무시
    if message.author == bot.user:
        return

    # 봇이 멘션됐을 때만 반응
    if bot.user not in message.mentions:
        return

    # Rate limit 체크
    if not check_rate_limit(message.author.id):
        await message.channel.send("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.")
        return

    # 멘션 제거한 실제 메시지
    content = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not content:
        await message.channel.send("무엇을 도와드릴까요? 매물 검색, 등록, 수정, 삭제, 통계, 비교가 가능합니다.")
        return

    # 대화 이력 관리
    channel_id = message.channel.id
    history = conversation_history[channel_id]

    async with message.channel.typing():
        try:
            response = await asyncio.wait_for(
                assistant.chat(content, history),
                timeout=120.0,
            )

            # 이력 추가
            history.append({"role": "user", "content": content})
            history.append({"role": "assistant", "content": response})

            # 이력 크기 제한
            if len(history) > MAX_HISTORY * 2:
                conversation_history[channel_id] = history[-(MAX_HISTORY * 2):]

            # 응답 전송 (2000자 초과 시 분할)
            await send_long_message(message.channel, response)

        except asyncio.TimeoutError:
            await message.channel.send("처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}", exc_info=True)
            await message.channel.send("오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


async def shutdown():
    """봇 종료 시 정리"""
    await assistant.disconnect_mcp()
    await bot.close()


def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        return
    bot.run(token)


if __name__ == "__main__":
    main()
