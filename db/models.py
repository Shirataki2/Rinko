from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.schema import ColumnDefault
from sqlalchemy.dialects.mysql import TINYINT, SMALLINT

meta = MetaData()

Table(
    'reminder', meta,
    Column('id', Integer(), primary_key=True, autoincrement=True),
    Column('guild', String(64), nullable=False),
    Column('user', String(64), nullable=False),
    Column('text', String(300), nullable=False),
    Column('start_at', DateTime(), nullable=False),
    Column('created_at', DateTime(), nullable=False),
)

Table(
    'reminder_channel', meta,
    Column('guild', String(64), unique=True, nullable=False),
    Column('channel', String(64), nullable=False),
)

Table(
    'reminder_call', meta,
    Column('guild', String(64), unique=True, nullable=False),
    Column('7d', Boolean()),
    Column('1d', Boolean()),
    Column('12H', Boolean()),
    Column('6H', Boolean()),
    Column('3H', Boolean()),
    Column('2H', Boolean()),
    Column('1H', Boolean()),
    Column('30M', Boolean()),
    Column('10M', Boolean()),
    Column('0M', Boolean()),
)

Table(
    'server_info', meta,
    Column('guild', String(64), unique=True, nullable=False),
    Column('locale', String(8), default=ColumnDefault('ja')),
    Column('prefix', String(8), default=ColumnDefault('r>')),
    Column('enable_quote', Boolean())
)

Table(
    'wallet', meta,
    Column('guild', String(64), unique=True, nullable=False),
    Column('user', String(64), nullable=False),
    Column('money', Integer(), nullable=False),
    Column('turnip', Integer(), nullable=False),
    Column('buy_at', DateTime(), nullable=False),
    Column('rotten_turnip', Integer(), nullable=False),
)

Table(
    'works', meta,
    Column('guild', String(64), nullable=False),
    Column('user', String(64), nullable=False),
    Column('date', DateTime(), nullable=False),
)

Table(
    'turnip', meta,
    Column('price', Float(), nullable=False),
    Column('type', String(20), nullable=False),
    Column('date', DateTime(), nullable=False),
)