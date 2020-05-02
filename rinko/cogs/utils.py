import discord
from discord.ext import commands

import logging
import asyncio
import glob
import random
import os

from time import perf_counter
from aiohttp import ClientSession

import rinko
from rinko.core.bot.rinko import Rinko
from rinko.core.logger import get_module_logger
from rinko.core.config import config
from rinko.core.commands import checks
from rinko.core.commands.utils import mention_to_id
from rinko.core.constant import *

logger = get_module_logger(__name__)

class Utils(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        '''
        Calculate latency between the bot and Discord.
        '''
        logger.debug('Execute the "ping" command.')
        start = perf_counter()
        await self.rinko.session.get('https://discordapp.com')
        end = perf_counter()
        discord_duration = (end - start) * 1000
        start = perf_counter()
        embed = discord.Embed(color=THEME_COLOR).set_author(name='⏳Please wait')
        m = await ctx.send(embed=embed)
        end = perf_counter()
        message_duration = (end - start) * 1000
        embed.description = f'{self.rinko.user.mention} is online.'
        embed.set_author(name='Pong!', icon_url=self.rinko.user.avatar_url)
        embed.add_field(name=f'Heartbeat latency is:', value=f'`{self.rinko.latency * 1000:.2f}` ms.')
        embed.add_field(name=f'Discord latency is:',
                        value=f'`{discord_duration:.2f}` ms.')
        embed.add_field(name=f'Message latency is:',
                        value=f'`{message_duration:.2f}` ms.')
        await m.edit(embed=embed)

    @commands.command()
    @checks.can_manage_guild()
    @commands.cooldown(1, 1, type=commands.BucketType.guild)
    async def prefix(self, ctx: commands.Context, prefix):
        '''
        Changes the command prefix.
        '''
        logger.debug('Execute the "prefix" command.')
        if prefix:
            if len(prefix) > 8:
                logger.warning('The prefix must be 8 characters or less.')
                return await ctx.send(f'The prefix must be 8 characters or less.')
            logger.debug('Changes the prefix.')
            await self.rinko.set_prefix(ctx.guild, prefix)
            return await ctx.send(f'The prefix changed to **{prefix}**')

    @commands.command()
    @commands.cooldown(10, 1, type=commands.BucketType.guild)
    async def rand(self, ctx, A = None, B = None):
        '''
        Returns a random number.
        no argument : Returns a fractional number between 0 and 1.
        1  argument : Returns a natural number between 0 and A.
        2  arguments: Returns the natural number between A and B.
        '''
        try:
            if A is None and B is None:
                return await ctx.send(f"{random.random():.5f}")
            elif B is None:
                A = int(A)
                if A < 1:
                    raise commands.BadArgument(f"'A' must be a natural number.")
                return await ctx.send(f"{random.randint(0, A)}")
            else:
                A = int(A)
                B = int(B)
                if B < A:
                    A, B = B, A
                if A < 1 or B < 1:
                    raise commands.BadArgument(f"'A' and 'B' must be a natural number.")
                return await ctx.send(f"{random.randint(A, B)}")
        except Exception as e:
            raise commands.BadArgument("NATURAL NUMBER: 'A' and 'B'")

    @commands.command()
    @commands.cooldown(1, 1, commands.BucketType.guild)
    async def invite(self, ctx):
        '''
        Displays the URL to invite the bot to the server.
        '''
        await ctx.send(f'{config.oauth2_url}')

    @commands.command()
    @commands.guild_only()
    async def server(self, ctx: commands.Context):
        '''
        Displays information about the server.
        '''
        guild: discord.Guild = ctx.guild
        embed = discord.Embed(title=f'{guild.name}', colour=0x4060e3)
        embed.set_thumbnail(url=str(guild.icon_url))
        embed.add_field(name='Region', value=f'{guild.region}')
        embed.add_field(name='ID', value=f'{guild.id}')
        embed.add_field(name='Members', value=f'{len(guild.members)}')
        embed.add_field(name='Owner', value=f'{guild.owner.mention}')
        embed.add_field(name='Text Channels', value=f'{len(guild.text_channels)}')
        embed.add_field(name='Voice Channels', value=f'{len(guild.voice_channels)}')
        embed.set_footer(text=f'Created at {guild.created_at.strftime("%Y/%m/%d %H:%M:%S")}')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def user(self, ctx: commands.Context, user=None):
        '''
        Displays information about the user.
        '''
        try:
            if not (member := [m for m in self.rinko.get_all_members() if mention_to_id(user)[0] == m.id][0]):
                member = ctx.author
        except:
            member = ctx.author
        member: discord.Member
        embed = discord.Embed(title=f'{member.name}', colour=member.color)
        embed.set_thumbnail(url=str(member.avatar_url))
        embed.add_field(name='Nickname', value=f'{member.display_name}')
        embed.add_field(name='ID', value=f'{member.id}')
        embed.add_field(name='Joined at', value=f'{member.joined_at.strftime("%y/%m/%d %H:%M:%S")}')
        embed.add_field(name='Status', value=f'{member.status}')
        if member.activity:
            embed.add_field(name='Activity', value=f'{member.activity.name}')
        embed.add_field(name='Is Bot?', value=f'{member.bot}')
        embed.add_field(name='Roles', value=f'{", ".join([role.name for role in member.roles])}')
        embed.set_footer(text=f'Created at: {member.created_at.strftime("%y/%m/%d %H:%M:%S")}')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def info(self, ctx: commands.Context):
        '''
        Displays information about this bot.
        '''
        bot = self.rinko
        appinfo: discord.AppInfo = await bot.application_info()
        shard = f'{bot.shard_id}/{bot.shard_count}' if bot.shard_id else 'False'
        embed = discord.Embed(title=f'{appinfo.name}', colour=THEME_COLOR)
        embed.set_thumbnail(url=str(appinfo.icon_url))
        embed.add_field(name='Version', value=f'**{rinko.__version__}**')
        embed.add_field(name='Developer', value=f'{appinfo.owner.mention}')
        embed.add_field(name='# of Servers', value=f'{len(bot.guilds)}')
        embed.add_field(name='# of Users', value=f'{len(bot.users)}')
        embed.add_field(name='Shard', value=shard)
        embed.add_field(name='Public/Private', value=f'{"Public" if appinfo.bot_public else "Private" }')
        embed.add_field(name='ID', value=f'{appinfo.id}')
        await ctx.send(embed=embed)

    @commands.command()
    async def set_autoquote(self, ctx:commands.Context, flag=True):
        await self.rinko.set_config(ctx.guild, 'enable_quote', bool(flag) )
        await ctx.send(f'**{"En" if bool(flag) else "Dis"}abled** automatic notification of quotes on this server.')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not await self.rinko.get_config(
                guild=message.guild,
                key='enable_quote',
                default=True):
            return
        urlregex = re.compile(
            r"(https?:\/\/(?:|ptb\.|canary\.)discordapp\.com\/channels\/[0-9]{18,19}\/[0-9]{18,19}\/[0-9]{18,19})"
        )
        if urls := urlregex.findall(message.content):
            for url in urls:
                await message.channel.send(embed=await self.generate_quote_embed(url))

    async def generate_quote_embed(self, url):
        idregex = re.compile(r"[0-9]{18,19}")
        guild_id, channel_id, message_id = [int(_id) for _id in idregex.findall(url)]
        if guild_id:
            try:
                channel: discord.TextChannel = await self.rinko.fetch_channel(channel_id)
                message: discord.Message = await channel.fetch_message(message_id)
            except discord.Forbidden as e:
                title = '🚫 You don\'t have permission to access the specified resource.'
                embed = discord.Embed(title=f'**{title}**', description=str(e), color=0xff0000)
                return embed
            embed = discord.Embed()
            embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
            embed.description = message.content + "\n[original message]({0})".format(url)
            if len(message.attachments) > 0:
                embed.set_image(url=message.attachments[0].url)
            timestamp = message.created_at.strftime("%Y/%m/%d %H:%M:%S")
            embed.set_footer(
                text="{0} at #{1} ({2})".format(message.guild.name, channel.name, timestamp)
            )
            return embed

def setup(bot):
    bot.add_cog(Utils(bot))