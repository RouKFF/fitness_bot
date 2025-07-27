from aiogram.types import BotCommand


bot_cmds = [
    BotCommand(command='/coaches', description='Информация о тренерах'),
    BotCommand(command='/groups', description='Информация о группах'),
    BotCommand(command='/today', description='Расписание на сегодня'),
    BotCommand(command='/week', description='Расписание на неделю')
]