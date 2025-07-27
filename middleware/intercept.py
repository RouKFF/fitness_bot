from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio
import logging

logger = logging.getLogger(__name__)


class FSMCancelMiddleware(BaseMiddleware):
    """
     для обработки FSM состояний в админке.
    Сценарий:
    - Когда бот находится в `FSM State` (например, ждет ввода нового значения поля модели),
      этот middleware проверяет, что именно прислал пользователь.
    - Если пользователь прислал `текстовое сообщение` (Message.text) — оно считается ожидаемым,
      и управление передаётся хендлеру.Дальше бот обработает текст и сменит состояние.
    - Если пользователь вместо текста:
        - нажал инлайн-кнопку (CallbackQuery),
        - ввёл команду (/start, /cancel и т.д.),
        - прислал фото, голос, файл, стикер и т.д.,
      то:
        - состояние (`FSM`) сбрасывается,
        - предыдущее сообщение бота (если было) удаляется,
        - пользователю показывается уведомление `❌ Действие отменено.`,
        - хендлер НЕ вызывается.

    Таким образом, пользователь может "отменить" изменение модели просто начав новое действие
    — не нужно вручную нажимать "отмена".

    Используется для защиты от случайных действий, пока ожидается ввод нового значения модели.
    """

    async def __call__(self, handler, event, data):
        state: FSMContext = data.get('state')
        bot = data.get('bot')
        if state is None:
            return await handler(event, data)

        current = await state.get_state()
        if isinstance(event, CallbackQuery) and (event.data.startswith('confirm') or event.data.startswith('group:')):
            return await handler(event, data)

        if current:
            if isinstance(event, Message) and event.text and event.text[0] != '/':
                return await handler(event, data)

            user_data = await state.get_data()
            msg_id = user_data.get('message_id')
            try:
                if isinstance(event, Message):
                    chat_id = event.chat.id
                    await bot.delete_message(chat_id, msg_id)
                    alert = await event.reply('❌ Действие отменено.')
                    await event.delete()
                    await asyncio.sleep(2)
                    await alert.delete()

                elif isinstance(event, CallbackQuery):
                    chat_id = event.message.chat.id
                    await bot.delete_message(chat_id, msg_id)
                    await event.answer('❌ Действие отменено.',
                                       show_alert=True)
                    await event.message.delete()
                    await asyncio.sleep(1)
                logger.info(f'Wrong event. Chat {chat_id}')
            except Exception:
                pass
            await state.clear()
            logger.info(f'Clear state. Chat {chat_id}')
            return

        return await handler(event, data)
