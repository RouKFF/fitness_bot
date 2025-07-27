from logic.schedules import enter_duration_logic, enter_start_time_logic, confirm_create_logic
from keyboards.schedules import ScheduleDayFactory
from keyboards import format_day_name
from logic.schedules import start_schedule_add_logic, choose_group_logic, cancel_calendar_logic, schedule_for_timedelta
from datetime import datetime
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from logic.admins import is_schedule
from logic.admins import create_model
from keyboards.admins import confirm_create_button
from logic.shared_logic import generate_preview_text
from logic.shared_logic import get_model_class, cast_value
from models.main import FIELD_LABELS
from keyboards.admins import fields_kb
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models import with_session
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import admin_main_kb, main_edit_kb, confirm_button, delete_button, get_kb_factory
from logic import require_admin, confirm_delete_model, change_field, add_link, del_link
from logic import get_data, confirm_groups_coach_del, select_item_by_name_and_id
from logic import get_name_and_id, get_name_and_prefix
from .shared_router import show_entities
import logging

logger = logging.getLogger(__name__)

admin_rt = Router()

# -------------------- Вспомогательные функции --------------------


async def show_alert(text, callback: CallbackQuery):
    await callback.answer(text=text,
                          show_alert=True)
    await callback.message.edit_text(text='Админ панель:',
                                     reply_markup=admin_main_kb())


# -------------------- FSM --------------------

class EditModel(StatesGroup):
    waiting_for_value = State()
    waiting_for_confirm = State()


class CreateModelFSM(StatesGroup):
    waiting_for_field_input = State()
    waiting_for_confirmation = State()

# -------------------- Главная панель --------------------


@admin_rt.message(Command('admin'))
@with_session()
@require_admin()
async def admin_main_command(message: Message, session: AsyncSession):

    await message.answer("Админ панель:", reply_markup=admin_main_kb())
    await message.delete()


@admin_rt.callback_query(F.data.startswith('admin_main'))
@with_session()
@require_admin()
async def admin_main_callback(callback: CallbackQuery, session: AsyncSession):

    await callback.message.edit_text("Админ панель:", reply_markup=admin_main_kb())
    await callback.answer()

# -------------------- Блоки моделей --------------------


@admin_rt.callback_query(F.data.startswith('admin_block') & F.data.not_contains('schedule'))
@with_session()
@require_admin()
async def open_model_block(callback: CallbackQuery, session: AsyncSession):

    text, name, prefix = get_name_and_prefix(callback)
    await callback.message.edit_text(text=text, reply_markup=main_edit_kb(name, prefix))
    await callback.answer()


# -------------------- Удаление --------------------


@admin_rt.callback_query(F.data.startswith('admin_delete_'))
@with_session()
@require_admin()
async def show_delete_button(callback: CallbackQuery, session: AsyncSession):

    name, id = get_name_and_id(callback)
    flag, text = await is_schedule(name, id, session)
    if not flag:
        await callback.message.edit_reply_markup(reply_markup=delete_button(name, id))
    else:
        await callback.message.edit_text(text=text,
                                         reply_markup=delete_button(name, id))
    await callback.answer()


@admin_rt.callback_query(F.data.startswith('confirm_del_'))
@with_session()
@require_admin()
async def confirm_delete_model_callback(callback: CallbackQuery, session: AsyncSession):

    text = await confirm_delete_model(callback, session)
    await show_alert(text, callback)

# -------------------- Изменение полей --------------------
IGNORED_FIELDS = {
    'group': ['coach_id'],
}


@admin_rt.callback_query(F.data.startswith('change_'))
@with_session()
@require_admin()
async def choose_field_to_edit(callback: CallbackQuery, session: AsyncSession):

    name, id = get_name_and_id(callback)
    item = await select_item_by_name_and_id(name, id, session)
    await callback.message.edit_text("Выберите поле для изменения", reply_markup=fields_kb(item))
    await callback.answer()


@admin_rt.callback_query(F.data.startswith('edit_field:'))
@with_session()
@require_admin()
async def start_edit_field(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    _, model_name, obj_id, field = callback.data.split(':')
    field_label = FIELD_LABELS[model_name][field]
    await callback.message.edit_text(f'Введите новое значение для поля: *{field_label}*', parse_mode='Markdown')
    await state.set_state(EditModel.waiting_for_value)
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    await state.update_data(
        model=model_name,
        obj_id=int(obj_id),
        field=field,
        message_id=callback.message.message_id
    )

    await callback.answer()


@admin_rt.message(EditModel.waiting_for_value)
@with_session()
@require_admin()
async def receive_new_value(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    value = message.text
    await message.delete()
    label = FIELD_LABELS[data['model']][data['field']]
    text = f'{label}: {value}\n\nПодтвердите изменение:'

    # Кнопка без передачи value
    await message.bot.edit_message_text(
        text=text,
        chat_id=message.chat.id,
        message_id=data['message_id'],
        reply_markup=confirm_button(data)  # без value
    )

    # Обновляем состояние и сохраняем value в FSM
    await state.set_state(EditModel.waiting_for_confirm)
    logger.info(f'Set state {await state.get_state()}. Chat {message.chat.id}')
    await state.update_data(value=value)


@admin_rt.callback_query(F.data.startswith('confirm_edit:'))
@with_session()
@require_admin()
async def confirm_field_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    model_name = data["model"]
    obj_id = data["obj_id"]
    field = data["field"]
    value = data["value"]

    text = await change_field(session, model_name, obj_id, field, value)
    await state.clear()
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    await show_alert(text, callback)


@admin_rt.callback_query(F.data.startswith('admin_add'))
@with_session()
@require_admin()
async def choose_field_to_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext):

    _, _, model_name = get_name_and_prefix(callback)
    fields = list(FIELD_LABELS[model_name].keys())
    ignored = IGNORED_FIELDS.get(model_name, [])
    fields = [f for f in fields if f not in ignored]
    await state.set_state(CreateModelFSM.waiting_for_field_input)
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')
    await state.update_data(
        class_name=model_name,
        fields=fields,
        values={},
        current_index=0,
        message_id=callback.message.message_id
    )
    field_label = FIELD_LABELS[model_name][fields[0]]
    await callback.message.edit_text(f'Введите новое значение для поля: *{field_label}*', parse_mode='Markdown')
    await callback.answer()


@admin_rt.message(CreateModelFSM.waiting_for_field_input)
@with_session()
@require_admin()
async def process_field_input(message: Message, session: AsyncSession, state: FSMContext):

    data = await state.get_data()
    class_name = data['class_name']
    fields = data['fields']
    current_index = data['current_index']
    values = data['values']
    current_field = fields[current_index]
    message_id = data['message_id']

    model_class = get_model_class(class_name)
    value = cast_value(model_class, current_field, message.text.strip())
    values[current_field] = value

    await message.delete()

    current_index += 1

    if current_index < len(fields):
        next_field = fields[current_index]
        field_label = FIELD_LABELS[class_name][next_field]

        await state.update_data(values=values, current_index=current_index)

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=f"Введите значение для поля: <b>{field_label}</b>",
            parse_mode='HTML'
        )

        await state.set_state(CreateModelFSM.waiting_for_field_input)
        logger.info(f'Set state {await state.get_state()}. Chat {message.chat.id}')

    else:
        # Все поля введены — финальное подтверждение
        model_cls = get_model_class(class_name)
        preview_text = await generate_preview_text(model_cls, values)

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=preview_text + "\n\nПодтвердите создание:",
            reply_markup=confirm_create_button(class_name),
            parse_mode='HTML'
        )

        await state.set_state(CreateModelFSM.waiting_for_confirmation)
        logger.info(f'Set state {await state.get_state()}. Chat {message.chat.id}')


@admin_rt.callback_query(F.data.startswith('confirm_create:') & F.data.not_contains('schedule'))
@with_session()
@require_admin()
async def confirm_create(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    text = await create_model(session, state)
    await show_alert(text, callback)
    await state.clear()
    logger.info(f'Set state {await state.get_state()}. Chat {callback.message.chat.id}')

# -------------------- Привязки (link/unlink) --------------------


@admin_rt.callback_query(F.data.startswith('admin_link_list'))
@with_session()
@require_admin()
async def show_available_link_targets(callback: CallbackQuery, session: AsyncSession):

    await show_entities(target=callback, session=session, admin=True)


@admin_rt.callback_query(F.data.startswith('admin_link') & F.data.not_contains('_page'))
@with_session()
@require_admin()
async def link_coach_group(callback: CallbackQuery, session: AsyncSession):

    text = await add_link(callback, session)
    await show_alert(text, callback)


@admin_rt.callback_query(F.data.startswith('admin_') & F.data.contains('_page'))
@with_session()
@require_admin()
async def show_linked_entities(callback: CallbackQuery, session: AsyncSession):

    await show_entities(target=callback, session=session, admin=True)


@admin_rt.callback_query(F.data.startswith('admin_unlink'))
@with_session()
@require_admin()
async def confirm_unlink_coach(callback: CallbackQuery, session: AsyncSession):

    text, id = await del_link(callback, session)
    await callback.message.edit_text(text=text, reply_markup=delete_button('group', id, 'coach'))


@admin_rt.callback_query(F.data.startswith('confirm_') & F.data.contains('_del') & F.data.not_contains('schedule'))
@with_session()
@require_admin()
async def confirm_unlink_coach_callback(callback: CallbackQuery, session: AsyncSession):

    text = await confirm_groups_coach_del(callback, session)
    await show_alert(text, callback)

# -------------------- Страница тренера --------------------


@admin_rt.callback_query(F.data.startswith('admin_') & F.data.not_contains('_page') & F.data.not_contains('schedule'))
@with_session()
@require_admin()
async def open_detail(callback: CallbackQuery, session: AsyncSession):

    data = await get_data(callback, session)
    await callback.message.edit_text(text=data['text'],
                                     reply_markup=get_kb_factory(data))
    await callback.answer()


@admin_rt.callback_query(F.data == 'admin_block_schedule')
@with_session()
@require_admin()
async def admin_schedule_calendar(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(
        "Выберите дату для просмотра расписания:",
        reply_markup=await SimpleCalendar().start_calendar()
    )
    await callback.answer()


class AddScheduleFSM(StatesGroup):
    choosing_group = State()
    entering_start_time = State()
    entering_duration = State()
    confirming = State()


@admin_rt.callback_query(SimpleCalendarCallback.filter())
@with_session()
@require_admin()
async def admin_schedule_show_day(callback: CallbackQuery, session: AsyncSession, callback_data: dict):
    selected, selected_date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        offset = (selected_date.date() - datetime.now().date()).days
        schedules, day, _ = await schedule_for_timedelta(session, offset)
        text = format_day_name(day)
        markup = ScheduleDayFactory(
            schedules=schedules, offset=offset, admin=True)
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@admin_rt.callback_query(F.data == 'admin_schedule_back_to_calendar')
@with_session()
@require_admin()
async def admin_schedule_back_to_calendar(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(
        "Выберите дату для просмотра расписания:",
        reply_markup=await SimpleCalendar().start_calendar()
    )
    await callback.answer()


@admin_rt.callback_query(F.data.startswith('admin_schedule_add:'))
@with_session()
@require_admin()
async def admin_schedule_start_add(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await start_schedule_add_logic(callback, session, state)


@admin_rt.callback_query(F.data.startswith('group:'), AddScheduleFSM.choosing_group)
@with_session()
@require_admin()
async def choose_group(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await choose_group_logic(callback, session, state)


@admin_rt.callback_query(SimpleCalendarCallback.filter(F.act == "CANCEL"))
@require_admin()
async def admin_schedule_cancel_calendar(callback: CallbackQuery, state: FSMContext):
    await cancel_calendar_logic(callback, state)


@admin_rt.message(AddScheduleFSM.entering_start_time)
@with_session()
@require_admin()
async def enter_start_time(message: Message, session: AsyncSession, state: FSMContext):
    await enter_start_time_logic(message, session, state)


@admin_rt.message(AddScheduleFSM.entering_duration)
@with_session()
@require_admin()
async def enter_duration(message: Message, session: AsyncSession, state: FSMContext):
    await enter_duration_logic(message, session, state)


@admin_rt.callback_query(F.data == "confirm_create:schedule", AddScheduleFSM.confirming)
@with_session()
@require_admin()
async def confirm_create(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await confirm_create_logic(callback, session, state)
