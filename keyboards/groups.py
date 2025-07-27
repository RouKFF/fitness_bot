from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import Group, Coach
from keyboards.shared_keyboard import back_button, edit_delete_buttons


page_size = 10


class GroupActionFactory:
    def __new__(cls,
                coach: Coach | None,
                page: int = 0,
                offset: int = -1,
                change_id: int = 0) -> InlineKeyboardMarkup:
        buttons = []
        postfix = ''
        prefix = 'admin_' if change_id else ''
        if change_id:
            prefix = f'{prefix}unlink_'
            postfix = f',group:{change_id}'

        if change_id:
            buttons.append(edit_delete_buttons(change_id, 'group'))

        # Тренер (если есть)
        if coach:
            buttons.append([
                InlineKeyboardButton(text=f'Тренер: {coach.name}',
                                     callback_data=f'{prefix}coach:{coach.id}{postfix}')
            ])
        else:
            if change_id:
                buttons.append([InlineKeyboardButton(text='➕ Добавить тренера',
                                                     callback_data=f'admin_link_list_coach:{change_id}')])
            else:
                buttons.append([InlineKeyboardButton(text='Тренер не назначен',
                                                     callback_data='noop')])

        # Назад к списку
        buttons.append(back_button('↩ Список групп',
                       f'{prefix}group_page:{page}'))

        # Назад к расписанию
        if offset != -1:
            buttons.append(back_button(
                '↩ Вернуться к расписанию', f'schedule:{offset}'))

        return InlineKeyboardMarkup(inline_keyboard=buttons)

# admin_unlink_coach:9
# admin_unlink_group:6
# 888701859