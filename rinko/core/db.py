import asyncio
import aiomysql
from aiomysql.sa import create_engine

from typing import Dict, List, Tuple, Any, Union

import discord
from discord.ext import commands

from rinko.core.config import config
from rinko.core.logger import get_module_logger

logger = get_module_logger(__name__)


class DB:
    def __init__(self, bot, *args, **kwargs):
        self.rinko = bot

    def setup(self):
        self.pool = self.rinko.loop.run_until_complete(self.get_db())

    async def get_db(self):
        try:
            return await aiomysql.create_pool(
                host=config.mysql_host,
                user=config.mysql_user,
                password=config.mysql_passwd,
                autocommit=True,
                db=config.mysql_db,
                loop=self.rinko.loop,
            )
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error('MySQLサーバとの接続に失敗しました')
            raise e

    async def __async_set(self, sql, args):
        await self.rinko.wait_until_ready()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
            await conn.commit()
        self.pool.close()
        await self.pool.wait_closed()

    async def __async_get(self, sql, args) -> Tuple[Dict[str, Any]]:
        await self.rinko.wait_until_ready()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                results = await cur.fetchall()
            await conn.commit()
        self.pool.close()
        await self.pool.wait_closed()
        return results

    async def set(self, sql, args):
        self.rinko.loop.run_until_complete(self.__async_set(sql, args))

    async def get(self, sql, args):
        return self.rinko.loop.run_until_complete(self.__async_get(sql, args))

    async def set_locale(self, ctx: commands.Context, locale: str):
        await self.set('REPLACE INTO server_info (guild, locale) VALUES (%s, %s);', (str(ctx.guild.id), locale))

    async def get_locale(self, ctx: commands.Context):
        results = await self.get('SELECT * FROM server_info guild = %s;', (str(ctx.guild.id)))
        try:
            return results[0]['locale']
        except KeyError:
            return None
