from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from models import with_session
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import CoachActionFactory
from logic.shared_logic import get_data
from .shared_router import show_entities

coaches_rt = Router()


@coaches_rt.message(Command('coaches'))
@with_session()
async def list_coaches(message: Message, session: AsyncSession):
    await show_entities(target=message,
                        session=session)
    await message.delete()


@coaches_rt.callback_query(F.data.startswith('coach_page:'))
@with_session()
async def paginate_coaches(callback: CallbackQuery, session: AsyncSession):
    await show_entities(target=callback,
                        session=session)


@coaches_rt.callback_query(F.data.startswith('coach:'))
@with_session()
async def coach_data(callback: CallbackQuery, session: AsyncSession):
    data = await get_data(callback, session)
    await callback.message.edit_text(text=data['text'],
                                     reply_markup=CoachActionFactory(groups=data['groups'],
                                                                     page=data['page']))
    await callback.answer()
