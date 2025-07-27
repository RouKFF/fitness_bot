from aiogram.types import InlineKeyboardButton

def back_button(text: str, callback: str) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text=text, callback_data=callback)]

def edit_delete_buttons(change_id: int, model: str) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(text='⚙️ Изменить', callback_data=f'change_{model}:{change_id}'),
        InlineKeyboardButton(text='🗑️ Удалить?', callback_data=f'admin_delete_{model}:{change_id}')
    ]
