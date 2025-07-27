from dotenv import load_dotenv
import os


def update_env_variable(filepath: str, key: str, new_value: str):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    with open(filepath, 'w') as file:
        for line in lines:
            if line.startswith(f"{key}="):
                file.write(f"{key}={new_value}\n")
            else:
                file.write(line)


load_dotenv()


async def rename_check(bot):

    if os.getenv('CHANGE_NAME') == 'true':
        await bot.set_my_name(os.getenv('NAME'))
        update_env_variable('.env', 'CHANGE_NAME', 'false')

    if os.getenv('CHANGE_DESCRIPTION') == 'true':
        await bot.set_my_short_description(os.getenv('DESCRIPTION_EN'), language_code='en')
        await bot.set_my_short_description(os.getenv('DESCRIPTION_RU'), language_code='ru')
        update_env_variable('.env', 'CHANGE_DESCRIPTION', 'false')

    if os.getenv('CHANGE_ABOUT') == 'true':
        await bot.set_my_description(os.getenv('ABOUT_EN'), language_code='en')
        await bot.set_my_description(os.getenv('ABOUT_RU'), language_code='ru')
        update_env_variable('.env', 'CHANGE_ABOUT', 'false')
