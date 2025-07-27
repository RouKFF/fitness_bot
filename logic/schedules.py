from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, Sequence
from typing import Tuple
from models import Schedule
from datetime import date, timedelta
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models import Schedule
from datetime import datetime, date, timedelta, time
from logic.shared_logic import generate_preview_text
from logic.admins import create_model, get_model_class
from keyboards.admins import confirm_create_button, admin_main_kb
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

logger = logging.getLogger(__name__)


async def schedule_for_timedelta(session: AsyncSession, offset: int = 0) -> Tuple[Sequence[Schedule], date, int]:
    """
    Проверка наличия занятий на день (сегодня + timedelta по `offset`) в бд. Выдает:
    - Последовательность (может быть пустой) из `schedules`:
    - Дату (сегодня + timedelta по `offset`):
    - Смещение `offset`:

    """
    today = date.today()+timedelta(days=offset)
    stmt = (select(Schedule).where(Schedule.day == today).order_by(Schedule.start_time)
            .options(selectinload(Schedule.group)))
    schedules = (await session.execute(stmt)).scalars().all()
    return schedules, today, offset


class AddScheduleFSM(StatesGroup):
    choosing_group = State()
    entering_start_time = State()
    entering_duration = State()
    confirming = State()


async def start_schedule_add_logic(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Начало добавления занятия: парсим дату из callback, сохраняем offset и дату в FSM, показываем список групп"""
    raw_value = callback.data.split(':')[1]

    try:
        offset = int(raw_value)
        lesson_date = date.today() + timedelta(days=offset)
    except ValueError:
        try:
            lesson_date = date.fromisoformat(raw_value)
            offset = (lesson_date - date.today()).days
        except ValueError:
            await callback.answer("❌ Неверный формат даты.", show_alert=True)
            return

    await state.set_state(AddScheduleFSM.choosing_group)
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    await state.update_data(class_name='schedule', offset=offset, values={"day": lesson_date})

    # импортируем чтобы избежать циклических зависимостей
    from routers.shared_router import show_entities
    await show_entities(callback, session)


async def choose_group_logic(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Выбор группы — обновляем FSM данными и переводим в состояние ввода времени"""
    group_id = int(callback.data.split(':')[1].split(',')[0])

    data = await state.get_data()
    data['values']['group_id'] = group_id
    await state.update_data(values=data['values'])
    await state.set_state(AddScheduleFSM.entering_start_time)
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    msg = await callback.message.edit_text("Введите время начала (формат HH:MM):")
    await state.update_data(fsm_msg_id=msg.message_id)


async def enter_start_time_logic(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ввода времени начала занятия, проверка формата, перевод в состояние ввода длительности"""
    from aiogram import Bot
    bot: Bot = message.bot
    chat_id = message.chat.id

    await clear_fsm_message(state, bot, chat_id)

    try:
        start_time = datetime.strptime(message.text, "%H:%M").time()
    except ValueError:
        err_msg = await message.answer("❌ Неверный формат. Введите время как HH:MM (например, 14:30).")
        await asyncio.sleep(3)
        await message.delete()
        await state.update_data(fsm_msg_id=err_msg.message_id)
        return

    await message.delete()

    data = await state.get_data()
    data['values']['start_time'] = start_time
    await state.update_data(values=data['values'])

    invite = await message.answer("Введите длительность в минутах:")
    await state.update_data(fsm_msg_id=invite.message_id)
    await state.set_state(AddScheduleFSM.entering_duration)
    logger.info(f'Set state {await state.get_state()}. Chat {message.chat.id}')


async def enter_duration_logic(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка ввода длительности занятия, проверка и подготовка предпросмотра"""
    from aiogram import Bot
    bot: Bot = message.bot
    chat_id = message.chat.id

    await clear_fsm_message(state, bot, chat_id)

    if not message.text.isdigit():
        err_msg = await message.answer("❌ Введите число минут.")
        await asyncio.sleep(3)
        await message.delete()
        await state.update_data(fsm_msg_id=err_msg.message_id)
        return

    await message.delete()
    duration = int(message.text)

    data = await state.get_data()
    data['values']['duration_minutes'] = duration
    await state.update_data(values=data['values'])

    model_cls = get_model_class(data['class_name'])
    preview = await generate_preview_text(model_cls, data['values'], session)

    await state.set_state(AddScheduleFSM.confirming)
    logger.info(f'Set state {await state.get_state()}. Chat {message.chat.id}')
    msg = await message.answer(
        f"Проверьте данные:\n\n{preview}",
        reply_markup=confirm_create_button('schedule')
    )
    await state.update_data(fsm_msg_id=msg.message_id)


async def confirm_create_logic(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработка подтверждения создания занятия, проверка занятости времени, создание записи"""
    from aiogram import Bot
    bot: Bot = callback.bot
    chat_id = callback.message.chat.id

    data = await state.get_data()
    values = data['values']

    is_available = await is_time_slot_available(
        session,
        values['group_id'],
        values['day'],
        values['start_time'],
        timedelta(minutes=values['duration_minutes'])
    )
    if not is_available:
        await callback.answer("❌ Время пересекается с другим занятием.", show_alert=True)
        return

    model_cls = get_model_class(data['class_name'])
    new_entity = await create_model(session, state)

    await callback.message.edit_text(
        f"✅ Запись добавлена:\n\n{new_entity}"
    )
    await asyncio.sleep(2)
    await clear_fsm_message(state, bot, chat_id)
    await state.clear()
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    await callback.answer()


async def cancel_calendar_logic(callback: CallbackQuery, state: FSMContext):
    """Отмена выбора даты в календаре"""
    await callback.message.edit_text(
        "Выбор даты отменён.",
        reply_markup=admin_main_kb()
    )
    await state.clear()
    await callback.answer()


async def clear_fsm_message(state: FSMContext, bot, chat_id: int):
    """Удаляет последнее сообщение, связанное с FSM, если есть"""
    data = await state.get_data()
    fsm_msg_id = data.get("fsm_msg_id")
    if fsm_msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=fsm_msg_id)
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение FSM: {e}")
        await state.update_data(fsm_msg_id=None)


async def is_time_slot_available(
    session: AsyncSession,
    group_id: int,
    day: date,
    start_time: time,
    duration: timedelta
) -> bool:
    """
    Проверяет, свободно ли указанное время для группы.
    Возвращает True, если нет пересечений с другими занятиями.
    """
    from sqlalchemy import select
    from models import Schedule

    # Новое занятие: начало и конец
    new_start_dt = datetime.combine(day, start_time)
    new_end_dt = new_start_dt + duration

    # Выбираем все занятия в тот же день и группе
    query = select(Schedule).where(
        Schedule.group_id == group_id,
        Schedule.day == day
    )

    result = await session.execute(query)
    schedules = result.scalars().all()

    for s in schedules:
        existing_start_dt = datetime.combine(s.day, s.start_time)
        existing_end_dt = existing_start_dt + \
            timedelta(minutes=s.duration_minutes)

        # Проверка на пересечение интервалов
        if not (existing_end_dt <= new_start_dt or existing_start_dt >= new_end_dt):
            return False  # Есть пересечение

    return True
