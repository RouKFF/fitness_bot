from sqlalchemy.inspection import inspect
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from models import Admin, Coach, Group, Schedule, Base
from typing import Callable, Tuple, Sequence, Type
from models.main import FIELD_LABELS, PAGE_SIZE
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, Sequence


def get_model_class(name: str) -> Type[Base]:
    """
    Возврат модели по названию. Пример:
    - `'coach' -> Coach`
    """
    return {
        'coach': Coach,
        'group': Group,
        'schedule': Schedule,
        'admin': Admin,
    }[name]


def cast_value(instance, field: str, value: str) -> any:
    """
    Приведение к нужному типу, либо просто возврат значения. Примеры:
    - Вход `object[Coach], 'age', '35'`
      - Выход `35`
    - Вход `object[Coach], 'age', 'Иван'`
      - Выход `'Иван'`
    """
    python_type = type(getattr(instance, field))
    try:
        return python_type(value)
    except Exception:
        return value


def get_name_and_id(callback: CallbackQuery) -> Tuple[str, int]:
    """
    Просто достает из колбека `name` и `id`
    """
    data = callback.data.split(':')
    name = data[0].split('_')[-1]
    id = int(data[1])
    return name, id


def get_change_id(data: str) -> int:
    """
    Просто достает из строки `id`
    """
    parts = data.split(',')
    return int(parts[0].split(':')[-1])


def get_name_and_prefix(model: str | CallbackQuery) -> Tuple[str, str, str]:
    """
    Принимает колбек `admin_block_{name(s)}`
    - Выдает по нему переменные `text`, `name`, `prefix`
    """
    if isinstance(model, CallbackQuery):
        temp = model.data.split('_')[-1]
    else:
        temp = model

    PREFIX_TO_LABELS = {
        'group': ('Группы:', 'группу'),
        'coach': ('Тренеры:', 'тренера'),
        'schedule': ('Расписание:', 'занятие'),
        'admin': ('Админы:', 'админа')
    }
    text = PREFIX_TO_LABELS[temp][0]
    name = PREFIX_TO_LABELS[temp][1]
    prefix = temp

    return text, name, prefix


async def get_total(item_cls_name: str, session: AsyncSession) -> int:
    """
    Количество всех элементов группы в бд
    """
    item_cls = get_model_class(item_cls_name)
    stmt = select(func.count()).select_from(item_cls)
    return await session.scalar(stmt)


async def get_model_from_event(event: Message | CallbackQuery) -> Tuple[str, int]:
    """
    Возврат названия модели и номера страницы из сообщения или колбека
    """
    if isinstance(event, Message):
        data = event.text
    elif isinstance(event, CallbackQuery):
        data = event.data
    if 'schedule_add' in data:
        return 'group', 0

    if 'page' in data:
        page = int(data.split(':')[1])
    else:
        page = 0

    model_name = 'admin'
    if 'coach' in data:
        model_name = 'coach'
    elif 'group' in data:
        model_name = 'group'
    return model_name, page


async def get_page(session: AsyncSession, event, unlinked: bool = False) -> Tuple[Sequence[Coach], int, int]:
    """
    Поиск тренеров в бд. Смещение поиска по странице
    - `callback` опционален, если нет то `page=0`
    - Выдает последовательность, страницу `page`, `page_size`
    """
    model_name, page = await get_model_from_event(event)
    model = get_model_class(model_name)
    page_size = PAGE_SIZE[model_name]
    offset = page * page_size
    stmt = select(model)
    if model_name == 'group' and unlinked:
        stmt = stmt.where(Group.coach_id.is_(None))
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all(), page, page_size


async def get_data(callback, session: AsyncSession) -> dict:
    """
    Информация о тренере/группе/админе
    """
    input = {
        "mode": None,
        'class': None,
        "id": None,
        "page": 0,
        "offset": -1
    }
    result = {}
# group:{id},schedule:{offset}
# admin_admin:{id},page:{page}
# coach:{id}
    parts = callback.data.split(',')
    if parts[0].startswith('admin'):
        input['mode'] = 'admin'
        parts[0] = parts[0].replace('admin_', '')
    input['class'], input['id'] = parts[0].split(':')
    if 'page' in parts[-1]:
        input['page'] = int(parts[-1].split(':')[1])
    else:
        input['page'] = 0
    if 'schedule' in parts[-1]:
        input['offset'] = int(parts[-1].split(':')[1])

    item_cls = get_model_class(input['class'])
    item_id = int(input['id'])
    stmt = select(item_cls).where(item_cls.id == item_id)

    match input['class']:
        case 'coach':
            stmt = stmt.options(selectinload(item_cls.groups))
            text = 'о тренере:'
        case 'group':
            stmt = stmt.options(selectinload(item_cls.coach))
            text = 'о группе:'
        case 'admin':
            text = 'об админе:'
    item = (await session.execute(stmt)).scalar_one_or_none()
    item_lst = []
    item_lst.append(f'Информация {text}\n')
    if item:
        mapper = inspect(item_cls)
        for field_prop in mapper.column_attrs:
            field = field_prop.key
            if field != 'id' and field != 'coach_id':
                field_value = getattr(item, field)
                item_lst.append(
                    f'{FIELD_LABELS[input['class']][field]}: {field_value}')
        result['text'] = '\n'.join(item_lst)
    else:
        result['text'] = 'Не удалось найти информацию'
    result['page'] = input['page']
    result['id'] = item_id
    match input['class']:
        case 'coach':
            result['groups'] = item.groups if item_lst else None
        case 'group':
            result['offset'] = input['offset']
            result['coach'] = item.coach if item_lst else None
    return result


async def generate_preview_text(model_cls: type, values: dict, session:AsyncSession) -> str:
    from .admins import select_item_by_name_and_id
    class_name = model_cls.__name__.lower()
    labels = FIELD_LABELS[class_name]
    text_lines = []
    for field in values:
        if field == 'day':
            text_lines.append(
                f"{labels[field]}: {values[field].strftime('%d.%m.%Y')}")
        elif field == 'start_time':
            text_lines.append(
                f"{labels[field]}: {values[field].strftime('%H:%M')}")
        elif field == 'duration_minutes':
            text_lines.append(f"{labels[field]}: {values[field]}  мин")
        elif field == 'group_id':
            group = await select_item_by_name_and_id('group', values[field], session)
            text_lines.append(f"{labels[field]}: {group.name}")
        else:
            text_lines.append(f"{labels[field]}: {values[field]}")
    return "\n".join(text_lines)
