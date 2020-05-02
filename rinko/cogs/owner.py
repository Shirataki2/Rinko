import discord
from discord.ext import commands

import logging
import asyncio
import glob
import tabulate
import random
import os

from time import perf_counter
from aiohttp import ClientSession

from rinko.core.bot.rinko import Rinko
from rinko.core.config import config
from rinko.core.logger import get_module_logger
from rinko.core.constant import *
from rinko.core.commands.utils import aexec

logger = get_module_logger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command()
    @commands.cooldown(1, 180, type=commands.BucketType.guild)
    async def feedback(self, ctx: commands.Context, *, message):
        '''
        Send feedback to the bot's developers.
        :heart: Please keep the contents under 1500 characters.
        '''
        embed = discord.Embed(title='Feedback!')
        if len(message) > 1500:
            return
        embed.description = message
        embed.add_field(name=f'Guild Name', value=f'{str(ctx.guild)}')
        embed.add_field(name=f'Guild ID', value=f'{ctx.guild.id}')
        embed.add_field(name=f'User Name', value=f'{ctx.author.mention}')
        embed.add_field(name=f'User ID', value=f'{ctx.author.id}')
        owner = self.rinko.get_user(int(config.owner_id))
        await owner.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    @commands.cooldown(1, 1)
    async def reload(self, ctx: commands.Context):
        '''
        Reloads all extensions.
        '''
        self.rinko.get_all_cogs(True)
        await ctx.send('All extensions has been reloaded.')

    @commands.is_owner()
    @commands.command(hidden=True)
    @commands.cooldown(1, 1)
    async def do(self, ctx, *, code):
        '''
        Run python script
        '''
        logger.debug(f"Execute Custom Code")
        await aexec(ctx, self.rinko, f'{code}')

    @commands.is_owner()
    @commands.command(hidden=True)
    @commands.cooldown(1, 1)
    async def sql(self, ctx, type, *, sql):
        '''
        Execute SQL Query
        '''
        logger.debug(f"Execute Custom Query: {sql}")
        if type == 'get':
            if results := await self.rinko.get(sql):
                table = tabulate.tabulate(results, headers="keys", tablefmt="fancy_grid")
                return await ctx.send(f'```\n{table}\n```')
        elif type == 'set':
            await self.rinko.set(sql)
        else:
            raise commands.BadArgument(f'\'type\' must be \'get\' or \'set\'')

def setup(bot):
    bot.add_cog(Owner(bot))