import discord
from discord.ext import commands, tasks

import logging
import asyncio
import aiofiles
import glob
import re
import random
import json
import shutil
import os
import tabulate
import httpx

from time import perf_counter
from datetime import datetime, timedelta, timezone
from aiohttp import ClientSession
from PIL import Image
from bs4 import BeautifulSoup
from io import BytesIO

import rinko
from rinko.core.bot.rinko import Rinko
from rinko.core.logger import get_module_logger
from rinko.core.config import config
from rinko.core.commands import checks
from rinko.core.commands.utils import mention_to_id
from rinko.core.constant import *
from rinko.core.extensions.music import Song, SongQueue, VoiceState, YoutubeDLSource


logger = get_module_logger(__name__)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command()
    @commands.cooldown(10, 1)
    async def lgtm(self, ctx: commands.Context):
        '''
        LOOKS GOOD TO ME!!!!!!
        '''
        url = 'https://www.lgtm.app/g'
        async with httpx.AsyncClient() as client:
            r:httpx.Response = await client.get(url)
        if r.status_code == 200:
            src = r.content
            soup = BeautifulSoup(src, "html.parser")
            imgs = soup.findAll('img', {'alt': 'LGTM image'})
            if imgs:
                img_url = imgs[0]['src']
                embed = discord.Embed(description=f'🇱 🇬 🇹 🇲 by **{ctx.author.mention}**')
                embed.set_image(url=img_url)
                await ctx.send(embed=embed)
                await ctx.message.delete()

    @commands.command()
    @commands.cooldown(1, 1, type=commands.BucketType.guild)
    async def markov(self, ctx: commands.Context, user:discord.Member=None, num_sentences=3):
        '''
        Generate fake sentences from statements said in the channel using the Markov chain algorithm.

        `user` argument is a target user to collect sentences. If nothing is specified, the user's statements will be targeted.
        '''
        if user is None:
            user:discord.Member = ctx.author
        starts = []
        seqtable = {}
        STOP_WORDS = ['.', '．', '。', '\n']
        async for message in ctx.channel.history(limit=100):
            if message.author != user:
                continue
            if message.content[0] == await self.rinko.get_prefix(message):
                continue
            words = self.rinko.tagger.parse(message.content).split(' ')
            starts.append(words[0])
            for word, n_word in zip(words[:-1], words[1:]):
                if word in seqtable:
                    seqtable[word].append(n_word)
                else:
                    seqtable[word] = [n_word]
                if word in STOP_WORDS:
                    starts.append(n_word)
        w = random.choice(starts)
        sc = 0
        result = w
        while sc < num_sentences or len(result) < 140:
            try:
                result += w + ' ' if re.fullmatch('[a-zA-Z]+', w) else ''
                w = random.choice(seqtable[w])
                if w in STOP_WORDS:
                    sc += 1
            except KeyError:
                result += '\n'
                sc += 1
                w = random.choice(starts)
        await ctx.send(re.sub('\n+','\n',result))

    @commands.command()
    @commands.cooldown(1, 1, type=commands.BucketType.guild)
    async def ojichat(self, ctx: commands.Context, user:discord.Member=None):
        '''
        (FOR JAPANESE USER) Rinkoﾁｬﾝ、オハヨウ〜😍😄🎵早く会いた、イナ（笑）🎵❗😘
        '''
        com = ctx.bot.get_cog('Command')
        usr = user.display_name if user else ctx.author.display_name
        await com.run(ctx, code=f'```sh\nojichat {usr}\n```')

    @commands.command()
    @commands.cooldown(1000, 86400)
    @commands.cooldown(1, 1, type=commands.BucketType.guild)
    async def weather(self, ctx: commands.Context, query, date=2):
        '''
        Displays the weather every 3 hours at the point of the query.
        Get the number of days specified in the 'date' argument (maximum 5 days).
        '''
        async with httpx.AsyncClient() as client, ctx.typing():
            if date > 5:
                return await ctx.send(f"❌You can get up to 5 days of weather")
            if date < 1:
                raise commands.BadArgument(f'The argument \'date\' must be an integer from 1 to 5, but {date} was given.')
            date = int(date)
            r: httpx.Response = await client.get(
                'https://api.openweathermap.org/data/2.5/forecast',
                params={
                    'appid': config.open_weather_apikey,
                    'q': query
                }
            )
            data = json.loads(r.content)
            if r.status_code == 404:
                await ctx.send(f"👀Location '{query}' could not be found.")
            elif r.status_code == 200:
                data = json.loads(r.content)
                weather_list = data['list']
                tz = data['city']['timezone']
                embed = discord.Embed(title=f'The weather in {query}', color=THEME_COLOR)
                formated = []
                await ctx.send(f'__**The weather in {query}**__\n\n')
                for i, weather in enumerate(weather_list[:8*date]):
                    time = datetime.fromtimestamp(weather['dt']).astimezone(timezone(timedelta(seconds=tz))).strftime('%m/%d %H:%M')
                    main = weather['main']
                    K = 273.15
                    temp = main['temp'] - K
                    temp_f = main['feels_like'] - K
                    p = main['pressure']
                    hm = main['humidity']
                    w = weather["weather"][0]["icon"]
                    w_icon = '❔'
                    if w in ['01d']:
                        w_icon = '☀️'
                    if w in ['01n']:
                        w_icon = '🌙'
                    if w in ['02d']:
                        w_icon = '🌤'
                    if w in ['03d', '04d', '02n', '03n', '04n']:
                        w_icon = '☁️'
                    if w in ['09d', '10d', '09n', '10n']:
                        w_icon = '☂️'
                    if w in ['13d', '13n']:
                        w_icon = '❄️'
                    if w in ['11d', '11n']:
                        w_icon = '⚡️'
                    if w in ['50d', '50n']:
                        w_icon = '🌫'
                    w_spd = weather['wind']['speed']
                    w_deg = weather['wind']['deg']
                    if w_deg < 22.5 or 360 - 22.5 <= w_deg:
                        w_dir = 'N'
                    elif 22.5 <= w_deg < 22.5 + 45:
                        w_dir = 'NE'
                    elif 22.5 + 45 <= w_deg < 22.5 + 45 * 2:
                        w_dir = 'E'
                    elif 22.5 + 45 * 2 <= w_deg < 22.5 + 45 * 3:
                        w_dir = 'SE'
                    elif 22.5 + 45 * 3 <= w_deg < 22.5 + 45 * 4:
                        w_dir = 'S'
                    elif 22.5 + 45 * 4 <= w_deg < 22.5 + 45 * 5:
                        w_dir = 'SW'
                    elif 22.5 + 45 * 5 <= w_deg < 22.5 + 45 * 6:
                        w_dir = 'W'
                    elif 22.5 + 45 * 6 <= w_deg < 22.5 + 45 * 7:
                        w_dir = 'NW'
                    formated.append(f'`{time}: ` {w_icon} ` {temp:4.1f} °C(feel {temp_f:4.1f} °C) {p:4d}hPa, Humid: {hm:4.1f}%, Wind: {w_spd:4.1f}m/s {w_dir}`')
                    if (i + 1) % 8 == 0:
                        await ctx.send('\n'.join(formated))
                        formated = []
                if formated:
                    await ctx.send('\n'.join(formated))


def setup(bot):
    bot.add_cog(Fun(bot))