from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher
from bot_config import rename_check
from bot_config.commands import bot_cmds
from routers import coaches_rt, groups_rt, schedules_rt, admin_rt
from middleware import FSMCancel

load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher()

dp.include_router(admin_rt)
dp.include_router(coaches_rt)
dp.include_router(groups_rt)
dp.include_router(schedules_rt)

dp.message.middleware(FSMCancel())
dp.callback_query.middleware(FSMCancel())


async def main():
    await rename_check(bot)
    await bot.set_my_commands(bot_cmds)
    await dp.start_polling(bot)
