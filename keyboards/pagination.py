from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def paginated_keyboard(items: list,
                       page: int,
                       total: int,
                       text_attr: str,
                       callback_prefix: str,
                       page_size: int,
                       admin: bool,
                       buttons_per_row: int = 2,
                       change_id: int = 0) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру с кнопками `items` и кнопками навигации:

    - Каждая кнопка из элемента списка: `{callback_prefix}:{item.id},page:{page}`
    - Кнопка Вперед и Назад: `{callback_prefix}_page:{page +- 1}`
    - Если `admin`, то добавляется кнопка возврата в админ меню
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    if change_id:
        callback_prefix = f'{callback_prefix}_{change_id}'
    for _, item in enumerate(items, start=1):
        text = getattr(item, text_attr)
        btn = InlineKeyboardButton(
            text=text,
            callback_data=f'{callback_prefix}:{item.id},page:{page}'
        )
        row.append(btn)
        if len(row) == buttons_per_row:
            kb.inline_keyboard.append(row)
            row = []

    if row:
        kb.inline_keyboard.append(row)

    nav_row = []

    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text='⇇ Назад',
            callback_data=f'{callback_prefix}_page:{page - 1}'
        ))
    else:
        nav_row.append(InlineKeyboardButton(text='←', callback_data='noop'))

    if (page + 1) * page_size < total:
        nav_row.append(InlineKeyboardButton(
            text='Вперед ⇉',
            callback_data=f'{callback_prefix}_page:{page + 1}'
        ))
    else:
        nav_row.append(InlineKeyboardButton(text='→', callback_data='noop'))

    if admin:
        kb.inline_keyboard.append([InlineKeyboardButton(text='↩ Админ меню',
                                                        callback_data='admin_main')])
    kb.inline_keyboard.append(nav_row)

    return kb
