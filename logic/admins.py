from .shared_logic import get_change_id
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Tuple, Sequence, Type
from aiogram.types import CallbackQuery, Message
from functools import wraps
from models import Admin, Coach, Group, Schedule, Base
from logic.shared_logic import get_name_and_id, get_model_class
from aiogram.fsm.context import FSMContext

from .shared_logic import cast_value
import logging

logger = logging.getLogger(__name__)


def require_admin():
    """
    Декоратор для проверки на админа по telegram id в бд
    """
    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(event, session, *args, **kwargs):
            from_user_id = event.from_user.id
            stmt = select(Admin).where(Admin.tg_id == from_user_id)
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is None:
                if hasattr(event, 'answer'):
                    return await event.answer('⛔ Недостаточно прав')
                if hasattr(event, 'message'):
                    return await event.message.answer('⛔ Недостаточно прав')
                return
            return await handler(event, session, *args, **kwargs)
        return wrapper
    return decorator

# общие


async def change_field(
    session: AsyncSession,
    model_name: str,
    obj_id: str,
    field: str,
    value: str
) -> str:
    model_class = get_model_class(model_name)
    instance = await session.get(model_class, int(obj_id))
    value = cast_value(instance, field, value)

    setattr(instance, field, value)
    try:
        await session.commit()
        return '✅ Изменено'
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f'Ошибка при изменении: {e}')
        return '❌ Ошибка БД при изменении'


async def select_item_by_name_and_id(name: str, id: int, session: AsyncSession) -> str:
    match name:
        case 'coach':
            result = await session.execute(select(Coach).where(Coach.id == id))
        case 'group':
            result = await session.execute(select(Group).where(Group.id == id))
        case 'schedule':
            result = await session.execute(select(Schedule).where(Schedule.id == id))
        case 'admin':
            result = await session.execute(select(Admin).where(Admin.id == id))
        case _:
            result = None
    obj = result.scalar_one_or_none()
    return obj


async def confirm_delete_model(callback: CallbackQuery, session: AsyncSession) -> Tuple[str, str]:
    """
    Удаление объекта модели из бд по `id`
    - Вход  `confirm_del_{name}:{id}`
    - Выход строка `str` Успешно/ Не успешно
    """
    name, id = get_name_and_id(callback)
    obj = await select_item_by_name_and_id(name, id, session)
    if obj is None:
        return '❌ Запись не найдена'
    try:
        await session.delete(obj)
        await session.commit()
        return '✅ Запись удалена'
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка при удалении: {e}")
        return '❌ Ошибка БД при удалении'


async def confirm_groups_coach_del(callback: CallbackQuery, session: AsyncSession) -> Tuple[str, str]:
    """
    Удаление привязки `Coach` обьекта `Group` из бд по `group_id`
    - Вход  `confirm_coach_del_group:{id}`
    - Выход строка `str` Успешно/ Не успешно
    """
    _, id = get_name_and_id(callback)
    try:
        stmt = (update(Group).where(Group.id == id).values(coach_id=None))
        await session.execute(stmt)
        await session.commit()
        return '✅ Тренер отвязан'
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка при удалении: {e}")
        return '❌ Ошибка БД при удалении'


async def add_link(callback: CallbackQuery, session: AsyncSession) -> str:
    """
    Привязка тренера к группе в бд по `id` и `link_id`
    - Вход  `admin_link_{model}_{link_id}:{id},page:{page}`
    - Выход строка `str` Успешно/ Не успешно
    """
    logger.warning(callback.data)
    data = callback.data.split(',')[0]
    id = int(data.split(':')[1])
    data = data.split(':')[0]
    model = data.split('_')[-2]
    link_id = int(data.split('_')[-1])
    match model:
        case 'coach':
            id, link_id = link_id, id
        case 'group':
            pass
        case _:
            return None
    stmt = (update(Group).where(Group.id == id).values(coach_id=link_id))
    try:
        await session.execute(stmt)
        await session.commit()
        return '✅ Запись добавлена'
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка при добавлении: {e}")
        return '❌ Ошибка БД при добавлении'


async def del_link(callback: CallbackQuery, session: AsyncSession) -> Tuple[str, int]:
    data = callback.data
    if 'coach' in data:
        data = data.split(',')[1]
    group_id = get_change_id(data)
    stmt = select(Group).where(Group.id == group_id).options(
        selectinload(Group.coach))
    group = (await session.execute(stmt)).scalar_one_or_none()
    text = f'Точно отвязать тренера {group.coach.name} {group.coach.surname} от группы {group.name} ?'
    return text, group_id


async def create_model(session: AsyncSession, state: FSMContext) -> str:
    try:
        data = await state.get_data()
        model_name = data['class_name']
        values = data['values']

        model_cls = get_model_class(model_name)
        instance = model_cls(**values)

        session.add(instance)
        await session.commit()
        return '✅ Успешно создано'
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f'Ошибка при создании: {e}')
        return '❌ Ошибка БД при создании'


async def is_schedule(name: str, id: int, session: AsyncSession) -> Tuple[bool, str]:
    if name != 'schedule':
        return False, ''
    schedule = await select_item_by_name_and_id(name, id, session)
    group = await select_item_by_name_and_id('group', schedule.group_id, session)
    text = f'Точно удалить занятие группы {group.name} {schedule.day.strftime('%d.%m.%Y')} в {schedule.start_time.strftime('%H:%M')} ({schedule.duration_minutes} мин)'
    return True, text
