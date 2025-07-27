from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, BigInteger
from datetime import date, time
from models import Base

FIELD_LABELS = {
    'coach': {
        'name': 'Имя',
        'surname': 'Фамилия',
        'sex': 'Пол',
        'age': 'Возраст',
        'experience': 'Стаж'
    },
    'group': {
        'name': 'Имя',
        'desc': 'Описание',
        'coach_id': 'Тренер',
    },
    'schedule': {
        'group_id': 'Группа',
        'day': 'День',
        'start_time': 'Время начала',
        'duration_minutes': 'Длительность'
    },
    'admin': {
        'name': 'Имя',
        'tg_id': 'Telegram ID',
    }

}
PAGE_SIZE = {
    'coach': 10,
    'group': 10,
    'admin': 10
}


class Coach(Base):
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    surname: Mapped[str] = mapped_column(String(50), nullable=False)
    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    age: Mapped[int]
    experience: Mapped[int]
    groups = relationship('Group', back_populates='coach')


class Group(Base):
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey(
        'coachs.id', ondelete='SET NULL'), nullable=True)
    coach = relationship('Coach', back_populates='groups')
    schedules = relationship(
        'Schedule', back_populates='group', cascade='all, delete-orphan')


class Schedule(Base):
    group_id: Mapped[int] = mapped_column(ForeignKey(
        'groups.id', ondelete='CASCADE'), nullable=False)
    group: Mapped['Group'] = relationship('Group', back_populates='schedules')
    day: Mapped[date] = mapped_column(nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    duration_minutes: Mapped[int] = mapped_column(default=60)


class Admin(Base):
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
