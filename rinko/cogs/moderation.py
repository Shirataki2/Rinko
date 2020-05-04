import discord
from discord.ext import commands

import logging
import asyncio
import glob
import random
import os

from time import perf_counter
from aiohttp import ClientSession
from durations import Duration

from rinko.core.bot.rinko import Rinko
from rinko.core.config import config
from rinko.core.logger import get_module_logger
from rinko.core.constant import *
from rinko.core.commands import checks
from rinko.core.commands.utils import aexec

logger = get_module_logger(__name__)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command(hidden=True)
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
        elif amount:
            channel: discord.TextChannel = ctx.channel
            logger.info(f'Delete {amount} messages.')
            await channel.purge(limit=amount)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def delete(self, ctx: commands.Context, amount: int):
        '''
        Deletes the specified amount of messages.
        Up to 50 messages can be deleted.
        You must have the "Message Management" privilege to run this program.
        '''
        if amount > 50:
            raise commands.BadArgument('The maximum number of messages that can be deleted is 50.')
        channel: discord.TextChannel = ctx.channel
        async for message in channel.history(limit=amount):
            await message.delete()
        msg: discord.Message = await ctx.send(f'Done')
        await asyncio.sleep(5)
        await msg.delete()

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def mute(self, ctx: commands.Context, user: discord.Member, *, reason='No reason'):
        '''
        Mutes the specified user and disallows them from speaking.
        '''
        guild: discord.Guild = ctx.guild
        for channel in guild.channels:
            channel: discord.TextChannel
            overwrite: discord.PermissionOverwrite = channel.overwrites_for(user)
            overwrite.send_messages = False
            await channel.set_permissions(user, overwrite=overwrite, reason=reason)
        embed = discord.Embed(title=f'🔇{user.display_name} muted!', description=reason, color=0xff0000)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def unmute(self, ctx: commands.Context, user: discord.Member, *, reason='No reason'):
        '''
        Unmutes the specified user.
        '''
        guild: discord.Guild = ctx.guild
        for channel in guild.channels:
            await channel.set_permissions(user, overwrite=None, reason=reason)
        embed = discord.Embed(title=f'🔈{user.display_name} unmuted!', description=reason, color=0x0000ff)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def tempmute(self, ctx: commands.Context, user: discord.Member, duration: str, *, reason='No reason'):
        '''
        Mutes the user for the specified time.
        Due to the specification, it is not possible to specify a mute for more than 48 hours because the temporary mute list is reset by restarting the Bot.
        '''
        dur = Duration(duration).to_seconds()
        if dur > 48 * 60 * 60:
            return await ctx.send('🚫 Too long temp mute duration!')
        await self.mute(ctx, user, reason=reason)
        await ctx.send(f'Mute for **{duration}** ({dur} seconds).')
        await asyncio.sleep(dur)
        await self.unmute(ctx, user, reason='Because the temporary mute duration has expired.')

    @commands.command()
    @commands.guild_only()
    @checks.can_ban()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def ban(self, ctx: commands.Context, user: discord.Member, *, reason='No reason'):
        '''
        Bans the specified user.
        '''
        await user.ban(reason=reason, delete_message_days=7)
        embed = discord.Embed(title=f'🚫 {user.display_name} banned!', description=reason, color=0xff0000)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @checks.can_ban()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def unban(self, ctx: commands.Context, user, *, reason='No reason'):
        '''
        Unbans the specified user.
        '''
        banned_users = await ctx.guild.bans()
        print(banned_users, user)
        for banned_entry in banned_users:
            banned_user = banned_entry.user
            if str(banned_user.id) == user.strip('<@!').strip('<@').strip('>'):
                await ctx.guild.unban(banned_user, reason=reason)
                embed = discord.Embed(title=f'🤗 {banned_user.name} unbanned!', description=reason, color=0x0000ff)
                return await ctx.send(embed=embed)
        else:
            return await ctx.send('😔User not found.')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def tempban(self, ctx: commands.Context, user: discord.Member, duration: str, *, reason='No reason'):
        '''
        Bans the user for the specified time.
        Due to the specification, it is not possible to specify a ban for more than 48 hours because the temporary mute list is reset by restarting the Bot.
        '''
        dur = Duration(duration).to_seconds()
        if dur > 48 * 60 * 60:
            return await ctx.send('🚫 Too long temp ban duration!')
        await self.ban(ctx, user, reason=reason)
        await ctx.send(f'Ban for **{duration}** ({dur} seconds).')
        await asyncio.sleep(dur)
        await self.unban(ctx, user.mention, reason='Because the temporary ban duration has expired.')


def setup(bot):
    bot.add_cog(Moderation(bot))
