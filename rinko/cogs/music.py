import discord
from discord.ext import commands, tasks

import logging
import asyncio
import aiofiles
import glob
import re
import random
import shutil
import math
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
from rinko.core.extensions.music import Song, SongQueue, VoiceState, YoutubeDLSource


logger = get_module_logger(__name__)

class Music(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot
        self.voice_states = {}

        self.heartbert.start()

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.rinko, ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    def cog_unload(self):
        self.heartbert.stop()
        for state in self.voice_states.values():
            self.rinko.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')
        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(invoke_without_subcommand=True)
    async def join(self, ctx: commands.Context):
        '''
        Makes the music playing Bot join the specified VC.
        Bot joins the channel in which you are participating.
        '''
        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            return await ctx.voice_state.voice.move_to(destination)
        ctx.voice_state.voice = await destination.connect()

    @commands.command()
    async def leave(self, ctx: commands.Context):
        '''
        Exit the bot and empty the playlist.
        '''
        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command()
    async def volume(self, ctx: commands.Context, *, volume: int):
        """
        Adjusts the volume between 0 and 200%.
        """

        if 0 > volume > 200:
            return await ctx.send('The volume should be between 0~200%.')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume is set to **{}%**.'.format(volume))

    @commands.command()
    async def speed(self, ctx: commands.Context, *, speed: int):
        """
        Changes the playback speed from 50 to 200% after the next song.
        """

        if 50 > speed or speed > 200:
            return await ctx.send('Speed should be between 50% and 200%.')
        ctx.voice_state.speed = speed / 100
        thres = ctx.voice_state.speed * 1000 / ctx.voice_state.pitch
        if thres < -0.5:
            pit = 2 * ctx.voice_state.speed * 1000
            import math
            q = math.log(pit / 1000) / math.log(2) * 12
            await ctx.send(f'The playback pitch is changed to about **{q:+.1f}** for the ffmpeg specification.')
            ctx.voice_state.pitch = pit
        await ctx.send('Speed is set to **{}%**.'.format(speed))

    @commands.command()
    async def pitch(self, ctx: commands.Context, *, pitch: float):
        """
        Changes the playback pitch from -12 to 12 after the next song.
        """

        if -12 > pitch or pitch > 12:
            return await ctx.send('Speed should be between -12 and 12.')

        ctx.voice_state.pitch = int(1000 * 2.0 ** (pitch / 12.0))
        thres = ctx.voice_state.speed * 1000 / ctx.voice_state.pitch
        if thres < -0.5:
            spd = .5 * ctx.voice_state.pitch / 1000
            await ctx.send(f'The playback speed is changed to {100*spd:.1f} for the ffmpeg specification.')
            ctx.voice_state.speed = spd
        ctx.voice_state.pitch_d = pitch
        await ctx.send(f'Pitch is set to **{pitch:+.1f}**.')

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def pause(self, ctx: commands.Context):
        """Pause"""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def resume(self, ctx: commands.Context):
        """Resume the song"""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def stop(self, ctx: commands.Context):
        """Stops playback and resets the track."""

        ctx.voice_state.queue.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def skip(self, ctx: commands.Context):
        """
        Skips the song currently playing.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing is playing.')
        ctx.voice_state.skip()
        return await ctx.send('Skipped')

    @commands.command(name='queue')
    async def queue(self, ctx: commands.Context, *, page: int = 1):
        """
        Displays the playlist.
        """

        if len(ctx.voice_state.queue) == 0:
            return await ctx.send('The playlist is empty.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.queue) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.queue[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.queue), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def shuffle(self, ctx: commands.Context):
        """
        Shuffles the songs in the playlist.
        """

        if len(ctx.voice_state.queue) == 0:
            return await ctx.send('The playlist is empty.')

        ctx.voice_state.queue.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def remove(self, ctx: commands.Context, index: int):
        """Removes songs of the specified index from the playlist."""

        if len(ctx.voice_state.queue) == 0:
            return await ctx.send('The playlist is empty.')

        ctx.voice_state.queue.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def loop(self, ctx: commands.Context):
        """
        Loops the current song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing is playing.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='play')
    async def play(self, ctx: commands.Context, *, query: str):
        """
        Fetches a song from the search query and if nothing has been added to the playlist, plays it immediately. If the song already has a playlist, the song will be added to the end of the playlist.
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self.join)

        async with ctx.typing():
            try:
                lists = await YoutubeDLSource.search(query, loop=self.rinko.loop)
                if lists:
                    source = await YoutubeDLSource.create_source(ctx, lists[0], loop=self.rinko.loop, speed=ctx.voice_state.speed, pitch=ctx.voice_state.pitch, pitch_d=ctx.voice_state.pitch_d)
                else:
                    ctx.send('No list')
            except Exception as e:
                await ctx.send('An error occurred during the processing of your request.: {}'.format(str(e)))
            else:
                song = Song(source)
                await ctx.voice_state.queue.put(song)
                await ctx.send('Added the following songs to the playlist.\n{}'.format(str(source)))

    @join.before_invoke
    @play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('First of all, join the VC!')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Join the same VC!')

    @tasks.loop(seconds=30)
    async def heartbert(self, ctx):
        for voice_state in self.voice_states.values():
            for song in voice_state.queue:
                if (sm := song.source.get('webpage_url_basename')) and sm[:2] == 'sm':
                    url = f'https://www.nicovideo.jp/watch/{sm}'
                    self.rinko.driver.get(url)
                    await asyncio.sleep(2)


def setup(bot):
    bot.add_cog(Music(bot))