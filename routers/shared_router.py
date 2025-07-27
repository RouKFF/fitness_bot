from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import paginated_keyboard, return_to_main_button
from logic.shared_logic import get_total, get_page, get_model_from_event, get_name_and_prefix, get_change_id
import logging

logger = logging.getLogger(__name__)


async def show_entities(target: Message | CallbackQuery,
                        session: AsyncSession,
                        model_name:str = '',
                        admin: bool = False):
    if not model_name:
        model_name, _ = await get_model_from_event(target)
    total = await get_total(model_name, session)
    change_id = 0

    if isinstance(target, Message):
        data = target.text
    elif isinstance(target, CallbackQuery):
        data = target.data
    logger.warning(data)
    _, name, callback_prefix = get_name_and_prefix(model_name)
    text = f'Выберите {name}'

    unlinked = False
    if 'link' in data:
        callback_prefix = f'link_{callback_prefix}'
        unlinked = True
        change_id = get_change_id(data)
        logger.warning(f'linked - {change_id}')
    

    entities, page, page_size = await get_page(session, target, unlinked)

    if admin:
        callback_prefix = f'admin_{callback_prefix}'
        if not entities:
            text = 'Нечего добавлять'
            if isinstance(target, Message):
                await target.answer(text, reply_markup=return_to_main_button())
            else:
                await target.message.edit_text(text, reply_markup=return_to_main_button())
                await target.answer()

    if model_name == 'coach':
        text_attr = 'surname'
    else:
        text_attr = 'name'

    markup = paginated_keyboard(
        items=entities,
        page=page,
        total=total,
        text_attr=text_attr,
        callback_prefix=callback_prefix,
        page_size=page_size,
        admin=admin,
        change_id=change_id
    )

    # Ответ
    logger.warning(markup.inline_keyboard[0][0].callback_data)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
