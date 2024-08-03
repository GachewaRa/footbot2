import asyncio
from telegram import Bot
import os
from bot import format_and_send_fixtures  # Import from your main bot file

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def run_scheduled_task():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await format_and_send_fixtures(bot)

def handler(event, context):
    asyncio.run(run_scheduled_task())
    return {'statusCode': 200, 'body': 'Scheduled task completed'}