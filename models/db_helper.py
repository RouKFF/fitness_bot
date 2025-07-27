import os
from dotenv import load_dotenv
from typing import AsyncGenerator, Callable
from functools import wraps
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW'))


class DBInstance:
    def __init__(self, url: str, echo: bool):
        self.engine = create_async_engine(
            url=url,
            echo=echo,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
            class_=AsyncSession
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session

    async def close(self):
        await self.engine.dispose()


DB_ENGINE = os.getenv('DB_ENGINE')

if 'sqlite' in DB_ENGINE:
    DB_DB = os.getenv('DB_DB')

    DB_URL = f'{DB_ENGINE}:///{DB_DB}'
else:
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_DB = os.getenv('DB_DB')

    DB_URL = f'{DB_ENGINE}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DB}'

DB_ECHO = os.getenv('DATABASE_ECHO', 'False') == 'True'

db = DBInstance(DB_URL, DB_ECHO)


def with_session():
    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(event, *args, **kwargs):
            async with db.get_session() as session:
                return await handler(event, session=session, *args, **kwargs)
        return wrapper
    return decorator
