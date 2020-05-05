import discord
from discord.ext import commands

import logging
import asyncio
import glob
import os

from aiohttp import ClientSession

from rinko.core.bot.base import RinkoBase
from rinko.core.config import config
from rinko.core.logger import get_module_logger
from rinko.core.constant import *

logger = get_module_logger(__name__)
class Rinko(RinkoBase):
    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix=self.get_prefix, *args, **kwargs)

    async def set_prefix(self, guild: discord.Guild, prefix: str):
        await self.set(f'UPDATE server_info SET prefix = "{prefix}" WHERE guild = "{guild.id}";')

    async def get_prefix(self, message: discord.Message):
        if prefix := await self.get(f'SELECT * FROM server_info WHERE guild = {message.guild.id}'):
            return prefix[0]['prefix']
        else:
            return DEFAULT_PREFIX

    async def set_config(self, guild: discord.Guild, key, value):
        await self.set(f'UPDATE server_info SET {key} = {value} WHERE guild = {guild.id};')

    async def get_config(self, guild: discord.Guild, key, default=None):
        if prefix := await self.get(f'SELECT * FROM server_info WHERE guild = {guild.id}'):
            return prefix[0][key]
        else:
            return default

    async def on_guild_join(self, guild):
        logger.debug(f'A new guild has joined: {guild.id}')
        await self.set('INSERT INTO server_info (guild, locale, prefix, enable_quote) VALUES (%s, "en", %s, 1);', (str(guild.id), DEFAULT_PREFIX))
        await self.set('INSERT INTO reminder_call (guild, 7d, 1d, 12H, 6H, 3H, 2H, 1H, 30M, 10M, 0M) VALUES (%s, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1);', (str(guild.id)))

    async def on_guild_remove(self, guild):
        logger.debug(f'A new guild has removed: {guild.id}')
        await self.set('DELETE FROM server_info WHERE guild = %s;', (str(guild.id)))
        await self.set('DELETE FROM reminder_call WHERE guild = %s;', (str(guild.id)))
