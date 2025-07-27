from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from models import with_session
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import GroupActionFactory
from logic.shared_logic import get_data
from .shared_router import show_entities

groups_rt = Router()


@groups_rt.message(Command('groups'))
@with_session()
async def list_groups(message: Message, session: AsyncSession):
    await show_entities(target=message,
                        session=session)
    await message.delete()


@groups_rt.callback_query(F.data.startswith('group_page:'))
@with_session()
async def paginate_groups(callback: CallbackQuery, session: AsyncSession):
    await show_entities(target=callback,
                        session=session)


@groups_rt.callback_query(F.data.startswith('group:'))
@with_session()
async def group_data(callback: CallbackQuery, session: AsyncSession):
    data = await get_data(callback, session)
    await callback.message.edit_text(text=data['text'],
                                     reply_markup=GroupActionFactory(coach=data['coach'],
                                                                     page=data['page'],
                                                                     offset=data['offset']))
    await callback.answer()
