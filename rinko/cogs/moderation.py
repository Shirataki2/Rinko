import discord
from discord.ext import commands

import logging
import asyncio
import glob
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

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def purge(self, ctx: commands.Context, amount: int):
        '''
        Deletes the specified amount of messages.
        Up to 100 messages can be deleted.
        You must have the "Message Management" privilege to run this program.
        '''
        logger.info('Execute "purge" command')
        if amount > 100:
            raise commands.BadArgument('The maximum number of messages that can be deleted is 100.')
            logger.info(f'Delete {amount} messages.')
        elif amount:
            channel: discord.TextChannel = ctx.channel
            await channel.purge(limit=amount)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def mute(self, ctx: commands.Context, user: discord.Member, *, reason='hoge'):
        guild: discord.Guild = ctx.guild
        muterole = guild.create_role(name='Muted', color=0xf34323)
        for channel in guild.channels:
            channel: discord.TextChannel
            overwrite:discord.PermissionOverwrite = channel.overwrites_for(user)
            overwrite.send_messages = False
            await channel.set_permissions(user, overwrite=overwrite, reason=reason)
        embed = discord.Embed(title=f'🔇{user.mention} muted!')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def unmute(self, ctx: commands.Context, user: discord.Member, *, reason='hoge'):
        guild: discord.Guild = ctx.guild
        for channel in guild.channels:
            await channel.set_permissions(user, overwrite=None, reason=reason)
        embed = discord.Embed(f'🔈{user.mention} unmuted!')
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(Moderation(bot))