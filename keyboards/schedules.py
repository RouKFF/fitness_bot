from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import Schedule
from datetime import date

WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг',
            'Пятница', 'Суббота', 'Воскресенье']


def format_day_name(day: date) -> str:
    """
    Возврат форматированной строки с днем недели и датой:
    - return `🔹 {weekday}, {day_str}`
    """
    day_str = day.strftime('%d.%m')
    weekday = WEEKDAYS[day.weekday()]
    if day == date.today():
        return f'📅 Сегодня, {weekday} ({day_str})'
    return f'🔹 {weekday}, {day_str}'


class ScheduleDayFactory:
    def __new__(cls,
                schedules: list[Schedule],
                offset: int,
                prefix: str = '',
                admin: bool = False) -> InlineKeyboardMarkup:
        buttons = []

        if schedules:
            for sched in schedules:
                time_str = sched.start_time.strftime('%H:%M')
                text = f'🕒 {time_str} - {sched.group.name} ({sched.duration_minutes} мин)'

                if admin:
                    callback = f'admin_delete_schedule:{sched.id}'
                else:
                    callback = f'{prefix}group:{sched.group.id},schedule:{offset}'

                buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])
        else:
            if not admin:
                buttons.append([InlineKeyboardButton(
                    text='Занятий на этот день нет',
                    callback_data='noop'
                )])

        if admin:
            # Кнопка добавления занятия
            buttons.append([InlineKeyboardButton(
                text='➕ Добавить занятие',
                callback_data=f'admin_schedule_add:{offset}'
            )])

            # Назад к календарю
            buttons.append([InlineKeyboardButton(
                text='↩ Назад к календарю',
                callback_data='admin_schedule_back_to_calendar'
            )])

        return InlineKeyboardMarkup(inline_keyboard=buttons)
