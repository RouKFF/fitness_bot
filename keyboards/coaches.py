from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import Group
from keyboards.shared_keyboard import back_button, edit_delete_buttons


page_size = 10


class CoachActionFactory:
    def __new__(cls,
                groups: list[Group],
                page: int = 0,
                change_id: int = 0) -> InlineKeyboardMarkup:
        buttons = []
        prefix = 'admin_' if change_id else ''
        group_prefix = f'{prefix}unlink_' if change_id else ''

        # Кнопки управления тренером
        if change_id:
            buttons.append(edit_delete_buttons(change_id, 'coach'))
            buttons.append([InlineKeyboardButton(text='➕ Добавить группу',
                                                 callback_data=f'{prefix}link_list_group:{change_id}')])

        # Группы тренера
        if groups:
            for group in groups:
                buttons.append([InlineKeyboardButton(
                    text=group.name,
                    callback_data=f'{group_prefix}group:{group.id}'
                )])
        elif not change_id:
            buttons.append([InlineKeyboardButton(
                text='Текущих групп нет', callback_data='noop')])

        # Назад к списку тренеров
        buttons.append(back_button('↩ Список тренеров',
                       f'{prefix}coach_page:{page}'))

        return InlineKeyboardMarkup(inline_keyboard=buttons)
