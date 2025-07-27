import urllib.parse
import json
from keyboards.shared_keyboard import back_button, edit_delete_buttons
from .groups import GroupActionFactory
from .coaches import CoachActionFactory
from models import Admin, Coach, Group, Schedule, Base
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Type
from models import Base
from models.main import FIELD_LABELS
from sqlalchemy.inspection import inspect

page_size = 10


def admin_main_kb() -> InlineKeyboardMarkup:
    """
    Возврат клавиатуры из списка моделей:
    - callback_data: `admin_block_{name}`
    """

    return InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text='Тренеры',
                              callback_data=f'admin_block_coach'),
         InlineKeyboardButton(text='Группы',
                              callback_data=f'admin_block_group')],
        [InlineKeyboardButton(text='Расписание',
                              callback_data=f'admin_block_schedule'),
         InlineKeyboardButton(text='Администраторы',
                              callback_data=f'admin_block_admin')]])


def main_edit_kb(name: str, prefix: str) -> InlineKeyboardMarkup:
    """
    Кнопки клавиатуры:
    - Добавить `{name}`: `admin_add_{prefix}`
    - Изменить/ Удалить `{name}`: `admin_{prefix}_page:0`
    - Возврат в админ меню: `admin_main`

    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'➕ Добавить {name}',
                              callback_data=f'admin_add_{prefix}')],
        [InlineKeyboardButton(text=f'⚙️🗑️ Изменить/ Удалить {name}',
                              callback_data=f'admin_{prefix}_page:0')],
        [InlineKeyboardButton(text=f'↩ Главное меню',
                              callback_data=f'admin_main')]])


def confirm_button(data: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура:
    - Подтвердить: `confirm_edit:{model}:{obj_id}:{field}`
    - Отменить: `admin_main`
    """
    model = data["model"]
    obj_id = data["obj_id"]
    field = data["field"]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text='✅ Подтвердить',
                callback_data=f'confirm_edit:{model}:{obj_id}:{field}'
            )],
            [InlineKeyboardButton(
                text='↩ Отменить',
                callback_data='admin_main'
            )]
        ]
    )


def confirm_create_button(model: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='✅ Подтвердить',
                                  callback_data=f'confirm_create:{model}')],
            [InlineKeyboardButton(text='↩ Отменить',
                                  callback_data='admin_main')]])


def delete_button(name: str, id: int, prefix: str = '') -> InlineKeyboardMarkup:
    """
    Клавиатура:
    - Подтвердить удаление: `confirm_{prefix_}del_{name}:{id}`
    - Отменить: `admin_main`
    """
    if prefix:
        prefix = f'{prefix}_'
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='‼️Подтвердить удаление‼️',
                                               callback_data=f'confirm_{prefix}del_{name}:{id}')],
                         [InlineKeyboardButton(text='↩ Отменить',
                                               callback_data='admin_main')]])


def return_to_main_button() -> InlineKeyboardMarkup:
    """
    Клавиатура:
    - Основное меню `admin_main`
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='↩ Основное меню',
                                               callback_data='admin_main')]])


def get_model_class(name: str) -> Type[Base]:
    """
    Возврат модели по названию. Пример:
    - `'Coach' -> Coach`
    """
    return {
        'coach': Coach,
        'goup': Group,
        'schedule': Schedule,
        'admin': Admin,
    }[name]


def fields_kb(item: Type[Base]) -> InlineKeyboardMarkup:
    mapper = inspect(item.__class__)
    buttons = []
    cls_name = item.__class__.__name__.lower()
    for field_prop in mapper.column_attrs:
        field = field_prop.key
        if field != 'id' and field != 'coach_id':
            field_value = getattr(item, field)
            field_label = FIELD_LABELS[cls_name][field]
            buttons.append([InlineKeyboardButton(text=f'{field_label}: {field_value}',
                                                 callback_data=f'edit_field:{cls_name}:{item.id}:{field}')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_kb_factory(data: dict):
    if 'offset' in data.keys():
        return GroupActionFactory(coach=data['coach'], page=data['page'], offset=data['offset'], change_id=data['id'])
    if 'groups' in data.keys():
        return CoachActionFactory(groups=data['groups'], page=data['page'], change_id=data['id'])
    else:
        return AdminActionFactory(change_id=data['id'], page=data['page'])


class AdminActionFactory:
    def __new__(cls,
                change_id: int,
                page: int = 0,
                ) -> InlineKeyboardMarkup:
        buttons = []
        prefix = 'admin_'

        buttons.append(edit_delete_buttons(change_id, 'admin'))
        buttons.append(back_button('↩ Список админов',
                                   f'{prefix}admin_page:{page}'))

        return InlineKeyboardMarkup(inline_keyboard=buttons)
