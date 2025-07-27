from aiogram import Router, F
import asyncio
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from models import with_session
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import format_day_name, ScheduleDayFactory
from logic import schedule_for_timedelta

schedules_rt = Router()


@schedules_rt.message(Command('today'))
@with_session()
async def today_schedule(message: Message, session: AsyncSession):
    schedules, today, offset = await schedule_for_timedelta(session)
    text = format_day_name(today)
    await message.answer(text=text,
                         reply_markup=ScheduleDayFactory(schedules, offset))
    await message.delete()


@schedules_rt.message(Command('week'))
@with_session()
async def week_schedule(message: Message, session: AsyncSession):
    await message.delete()
    for weekday in range(7):
        schedules, day, offset = await schedule_for_timedelta(session, weekday)
        text = format_day_name(day)
        await message.answer(text=text,
                             reply_markup=ScheduleDayFactory(schedules, offset))
        await asyncio.sleep(0.2)  # защита от flood


@schedules_rt.callback_query(F.data.startswith('schedule:'))
@with_session()
async def day_data(callback: CallbackQuery, session: AsyncSession):
    weekday = int(callback.data.split(':')[1])
    schedules, day, offset = await schedule_for_timedelta(session, weekday)
    text = format_day_name(day)
    await callback.message.edit_text(text=text,
                                     reply_markup=ScheduleDayFactory(schedules, offset))
