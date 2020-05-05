import discord
from discord.ext import commands, tasks

import logging
import asyncio
import aiofiles
import glob
import re
import random
import shutil
import os
import httpx

from time import perf_counter
from datetime import datetime
from aiohttp import ClientSession
from PIL import Image
from io import BytesIO

import rinko
from rinko.core.bot.rinko import Rinko
from rinko.core.logger import get_module_logger
from rinko.core.config import config
from rinko.core.commands import checks
from rinko.core.commands.utils import mention_to_id
from rinko.core.constant import *


logger = get_module_logger(__name__)

class Reminder(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot
        self.col2msg = {
            '7d': 'Next week, the following events will be held',
            '1d': 'In 24 hours, the following events will be held',
            '12H': 'In 12 hours, the following events will be held',
            '6H': 'In 6 hours, the following events will be held',
            '3H': 'In 3 hours, the following events will be held',
            '2H': 'In 2 hours, the following events will be held',
            '1H': 'In 1 hour, the following events will be held',
            '30M': 'In 20 minutes, the following events will be held',
            '10M': 'In 10 minutes, the following events will be held',
            '0M': 'The following events will be held soon.'
        }
        self.notification_loop.start()
        logger.debug('Notification Loop Started')

    def cog_unload(self):
        self.notification_loop.cancel()



    @commands.group(aliases=['rmd'])
    @commands.guild_only()
    async def reminder(self, ctx):
        '''
        Create, edit and delete reminders.
        '''
        logger.debug('reminder command invoked')
        if ctx.invoked_subcommand is None:
            await ctx.send(f'Enter a subcommand.')

    async def get_reminder_channel(self, guild: discord.Guild):
        r = await self.rinko.get(f'SELECT * FROM reminder_channel WHERE guild = {guild.id}')
        if len(r) > 0:
            return guild.get_channel(int(r[0]['channel']))
        else:
            return None

    @reminder.command()
    @checks.can_manage_guild()
    @commands.guild_only()
    async def init(self, ctx: commands.Context):
        '''
        Execute this command on the channel where you want to receive the reminder.
        '''
        logger.debug(f'Initialize reminder: {ctx.guild.id}')
        guild: discord.Guild = ctx.guild
        pres_channel = ctx.channel
        if prev_channel := await self.get_reminder_channel(guild):
            await self.rinko.set(f'UPDATE reminder_channel SET channel = "{pres_channel.id}" WHERE guild = "{prev_channel.id}"')
            await ctx.send(f'Changed the reminder notification channel from {prev_channel.mention} to {pres_channel.mention}.')
        else:
            await self.rinko.set(f'INSERT INTO reminder_channel (guild, channel) VALUES ("{guild.id}", "{pres_channel.id}")')
            await ctx.send(f'{pres_channel.mention} has been added to the reminder notification channel.')

    @reminder.command(name='set_notification')
    @checks.can_manage_guild()
    @commands.guild_only()
    async def set_notification(self, ctx: commands.Context, key, flag):
        '''
        Set the time to receive the notification.

        Keys can be selected from the following
        7d: 7 days ago
        1d: 1 day ago
        12H: 12 hours ago
        6H: 6 hours ago
        3H: 3 hours ago
        2H: 2 hours ago
        1H: 1 hour ago
        30M: 30 minutes ago.
        10M: 10 minutes ago.
        0M: Event start time.

        The flag is 0 for disabled and 1 for enabled.
        '''
        if (channel := await self.get_reminder_channel(ctx.guild)) is None:
            return await ctx.send('Please initialize the reminder first.\nExecute `reminder init` on the channel where you want to be notified.')
        if key not in self.col2msg.keys():
            ctx.send(f'Invalid key: {key}')
        await self.rinko.set(f'UPDATE reminder_call SET {key} = {flag} WHERE guild = {ctx.guild.id};')
        await ctx.send(f'The reminder settings have been overwritten.')
        await self.get_notification(ctx)

    @reminder.command(name='get_notification')
    @checks.can_manage_guild()
    @commands.guild_only()
    async def get_notification(self, ctx: commands.Context):
        '''
        Displays the time to receive the notification.

        7d: 7 days ago
        1d: 1 day ago
        12H: 12 hours ago
        6H: 6 hours ago
        3H: 3 hours ago
        2H: 2 hours ago
        1H: 1 hour ago
        30M: 30 minutes ago.
        10M: 10 minutes ago.
        0M: Event start time.

        The flag is 0 for disabled and 1 for enabled.
        '''
        if (channel := await self.get_reminder_channel(ctx.guild)) is None:
            return await ctx.send('Please initialize the reminder first.\nExecute `reminder init` on the channel where you want to be notified.')
        calls = await self.rinko.get(f"SELECT * FROM reminder_call WHERE guild = {ctx.guild.id}")
        if calls:
            call = calls[0]
            msg = '\n'.join([f'{col:<4}: {call[col]}' for col in self.col2msg.keys()])
            await ctx.send(f'```\n{msg}\n```')


    @reminder.command()
    @checks.can_manage_guild()
    @commands.guild_only()
    async def create(self, ctx: commands.Context):
        '''
        Set a new reminder interactively.
        '''
        guild: discord.Guild = ctx.guild
        if (channel := await self.get_reminder_channel(guild)) is None:
            return await ctx.send('Please initialize the reminder first.\nExecute `reminder init` on the channel where you want to be notified.')
        del_msgs = [ctx.message]
        del_msgs.append(await ctx.send(f'Create a new reminder.'))
        def text_checker(message:discord.Message):
            if len(message.content) > 100:
                return False
            return message.author == ctx.author
        def date_checker(message:discord.Message):
            txt = message.content
            try:
                [y, m, d, H, M] = [int(e) for e in txt.split('-')]
            except:
                return False
            return message.author == ctx.author
        try:
            del_msgs.append(await ctx.send(f'Please write briefly about your event. (100 words or less)\nIf you want to cancel, please send `//c`.'))
            msg = await self.rinko.wait_for('message', check=text_checker)
            text = msg.content
            if text == '//c':
                await ctx.send(f'Canceled')
                for msg in del_msgs:
                    await msg.delete()
                return
            user:discord.User = ctx.author
            guild:discord.Guild = ctx.guild
            del_msgs.append(msg)
        except:
            await ctx.send(f'An error occurred while writing the event.')
            for msg in del_msgs:
                await msg.delete()
            return
        try:
            del_msgs.append(await ctx.send(f'Please state the date and time of the event.\nSeparate the date and time with hyphens, such as `2020-10-31-23-45`.\nIn case of cancellation, please send `9999-99-99-99-99-99`.'))
            msg = await self.rinko.wait_for('message', check=date_checker, timeout=300)
            if text == '9999-99-99-99-99':
                await ctx.send(f'Canceled')
                for msg in del_msgs:
                    await msg.delete()
                return
            [y, m, d, H, M] = [int(e) for e in msg.content.split('-')]
            sql = 'INSERT INTO reminder (guild, user, text, start_at, created_at) VALUES (%s, %s, "%s", "%s", "%s");'
            try:
                await self.rinko.set(sql % (
                    str(guild.id),
                    str(ctx.author.id),
                    text,
                    f'{y}/{m}/{d} {H}:{M}',
                    datetime.now().strftime('%Y/%m/%d %H:%M')
                ))
            except:
                return await ctx.send('Incorrect date format.')
            emb = discord.Embed(
                title=text,
                color=0xe340e3,
                inline=False
            )
            emb.add_field(name='Date', value=datetime(y, m, d, H, M, 0, 0).strftime('%Y/%m/%d %H:%M'))
            emb.add_field(name='Created by', value=user.mention)
            del_msgs.append(msg)
            await channel.send('New reminder created.', embed=emb)
        except KeyboardInterrupt:
            await ctx.send(f'An error occurred while writing the database.')
        finally:
            for msg in del_msgs:
                await msg.delete()

    @reminder.command(name='list')
    @commands.guild_only()
    async def get(self, ctx: commands.Context):
        '''
        Displays a list of reminders.
        '''
        if (channel := await self.get_reminder_channel(ctx.guild)) is None:
            return await ctx.send('Please initialize the reminder first.\nExecute `reminder init` on the channel where you want to be notified.')
        user:discord.User = ctx.author
        guild:discord.Guild = ctx.guild
        results = await self.rinko.get(f'SELECT * FROM reminder WHERE guild = {guild.id} AND start_at > NOW() ORDER BY start_at;')
        if len(results) > 0:
            emb = discord.Embed(title='Reminder List', color=0xe34023)
        else:
            emb = discord.Embed(title='There are no reminders now.', color=0xe34023)
        for result in results:
            emb.add_field(name=f'{result["start_at"]} - <ID:**{result["id"]:07d}**>', value=f"**{result['text']}**", inline=False)
        await ctx.send(embed=emb)

    @reminder.command(name='delete')
    @commands.guild_only()
    async def delete(self, ctx: commands.Context, id:str):
        '''
        Deletes the reminder of the specified ID.
        '''
        if (channel := await self.get_reminder_channel(ctx.guild)) is None:
            return await ctx.send('Please initialize the reminder first.\nExecute `reminder init` on the channel where you want to be notified.')
        user:discord.User = ctx.author
        guild:discord.Guild = ctx.guild
        try:
            id = int(id)
        except:
            return await ctx.send(f'Invalid arguments.')
        results = await self.rinko.get(f'SELECT * FROM reminders WHERE guild = {guild.id} AND id = {id};')
        if len(results) == 0:
            return await ctx.send(f'There is no reminder for the specified ID.')
        try:
            self.rinko.set(f'DELETE FROM reminders WHERE guild = {guild.id} AND id = {id};')
        except:
            await ctx.send(f'An error occurred during deletion.')
        await ctx.send(f'Successfully deleted.')

    @tasks.loop(minutes=1)
    async def notification_loop(self):
        logger.info('Notification Loop')
        col2sql = {
            '7d': '(start_at >= DATE_ADD(NOW(), INTERVAL 10080 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 10081 MINUTE))',
            '1d': '(start_at >= DATE_ADD(NOW(), INTERVAL 1440 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 1441 MINUTE))',
            '12H': '(start_at >= DATE_ADD(NOW(), INTERVAL 720 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 721 MINUTE))',
            '6H': '(start_at >= DATE_ADD(NOW(), INTERVAL 360 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 361 MINUTE))',
            '3H': '(start_at >= DATE_ADD(NOW(), INTERVAL 180 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 181 MINUTE))',
            '2H': '(start_at >= DATE_ADD(NOW(), INTERVAL 120 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 121 MINUTE))',
            '1H': '(start_at >= DATE_ADD(NOW(), INTERVAL 60 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 61 MINUTE))',
            '30M': '(start_at >= DATE_ADD(NOW(), INTERVAL 30 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 31 MINUTE))',
            '10M': '(start_at >= DATE_ADD(NOW(), INTERVAL 10 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 11 MINUTE))',
            '0M': '(start_at >= DATE_ADD(NOW(), INTERVAL 0 MINUTE)) AND (start_at < DATE_ADD(NOW(), INTERVAL 1 MINUTE))',
        }
        col2msg = self.col2msg
        for guild in self.rinko.guilds:
            if (channel := await self.get_reminder_channel(guild)) is None:
                continue
            calls = await self.rinko.get(f"SELECT * FROM reminder_call WHERE guild = {guild.id}")
            if calls:
                calls = calls[0]
                for col in col2sql.keys():
                    if calls[col] == 0:
                        continue
                    emb = discord.Embed(title=col2msg[col], color=THEME_COLOR)
                    events = await self.rinko.get(f'SELECT * FROM reminder WHERE guild = {guild.id} AND {col2sql[col]}')
                    for event in events:
                        logger.debug(f'{guild.name} Calls detected')
                        logger.debug(f'\tSearch: {col}')
                        logger.debug(f'\t\tEvent: {event["text"]}')
                        emb.add_field(name=f'{event["start_at"]} - <ID:**{event["id"]:07d}**>', value=f"{event['text']}")
                    if events:
                        await channel.send(embed=emb)


def setup(bot):
    bot.add_cog(Reminder(bot))