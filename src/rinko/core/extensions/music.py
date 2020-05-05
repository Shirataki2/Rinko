import discord
from discord.ext import commands, tasks

import logging
import asyncio
import aiofiles
import glob
import re
import functools
import itertools
import random
import shutil
import os
import httpx
import youtube_dl
from youtube_dl.extractor import niconico
from async_timeout import timeout


from rinko.core.constant import *
from rinko.core.bot.rinko import Rinko

youtube_dl.utils.bug_reports_message = lambda: ''

class YoutubeDLException(Exception):
    pass

class VoiceError(Exception):
    pass

class YoutubeDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data:dict, volume=1.0, speed=1.0, pitch=1000, pitch_d=0):
        super().__init__(source, volume=volume)
        self.requester = ctx.author
        self.channel = ctx.channel
        self.speed = speed
        self.pitch = pitch
        self.pitch_d = pitch_d
        self.data = data
        self.uploader = data.get('uploader')
        try:
            self.asr = int(data.get('asr'))
        except:
            self.asr = 44100
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = f'{date[0:4]}/{date[4:6]}/{date[6:8]}'
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')
        self.webpage_base_name = data.get('webpage_url_basename')

    def __str__(self):
        return f'{self.title} by {self.uploader}\n{self.url}'

    @staticmethod
    def parse_duration(duration:int):
        M, S = divmod(duration, 60)
        H, M = divmod(M, 60)
        D, H = divmod(H, 24)
        duration = ''
        duration += f'{D} days ' if D > 0 else ''
        duration += f'{H} hours ' if H > 0 else ''
        duration += f'{M} minutes ' if M > 0 else ''
        duration += f'{S} seconds ' if S > 0 else ''
        duration = duration.strip()
        return duration

    @classmethod
    async def nico_search(cls, query: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, functools.partial(cls.ytdl.extract_info, query, download=False, process=False))
        f = sorted(data['formats'], key=lambda x: -x['abr'])[0]
        for k, v in f.items():
            data[k] = v
        print(data)
        return data


    @classmethod
    async def search(cls, query: str, *, loop: asyncio.BaseEventLoop = None):
        #TODO ニコ動のHEARTBEAT対策
        if re.search('###nicovideo.jp###', query):
            data = await YoutubeDLSource.nico_search(query, loop=loop)
        else:
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, functools.partial(cls.ytdl.extract_info, query, download=False, process=False))
        if data is None:
            raise YoutubeDLException('Couldn\'t find anything that matches `{}`'.format(search))
        process_info_list = []
        if 'entries' not in data:
            process_info_list.append(data)
        else:
            for entry in data['entries']:
                if entry:
                    process_info_list.append(data)
        if len(process_info_list) == 0:
            raise YoutubeDLException('Couldn\'t find anything that matches `{}`'.format(search))
        return process_info_list

    @classmethod
    async def create_source(cls, ctx, process_info: dict, *, loop: asyncio.BaseEventLoop = None, speed=1.0, pitch=1.0, pitch_d=1.0):
        webpage_url = process_info['webpage_url']
        processed_info = await loop.run_in_executor(None, functools.partial(cls.ytdl.extract_info, webpage_url, download=False))
        if processed_info is None:
            raise YoutubeDLException('Couldn\'t fetch `{}`'.format(webpage_url))
        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YoutubeDLException('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        if pitch == 1000 and speed == 1.0:
            return cls(ctx, discord.FFmpegPCMAudio(
                info['url'],
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options=f'-vn'
            ), data=info, speed=speed, pitch=pitch, pitch_d=pitch_d)
        else:
            return cls(ctx, discord.FFmpegPCMAudio(
                info['url'],
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options=f'-vn -af asetrate={info["asr"]}*{pitch}/1000,atempo={speed},atempo=1000/{pitch}'
            ), data=info, speed=speed, pitch=pitch, pitch_d=pitch_d)


class Song:
    __slots__ = ('source', 'requester')
    def __init__(self, source):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = discord.Embed(title='Now playing', colour=THEME_COLOR)
        embed.description = f'```css\n{self.source.title}\n```'
        embed.add_field(name='DURATION', value=self.source.duration)
        embed.add_field(name='SPEED', value=f'{self.source.speed*100:.1f}')
        embed.add_field(name='PITCH', value=f'{self.source.pitch_d:+.1f}')
        embed.add_field(name='REQUEST BY', value=self.requester.mention)
        embed.add_field(name='UPLOADER', value=f'[{self.source.uploader}]({self.source.uploader_url})')
        embed.add_field(name='URL', value=f'[Click]({self.source.url})')
        embed.set_thumbnail(url=self.source.thumbnail)
        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, idx):
        del self._queue[idx]

class VoiceState:
    def __init__(self, rinko: Rinko, ctx: commands.Context):
        self.rinko = rinko
        self._ctx = ctx
        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.queue = SongQueue()
        self._loop = False
        self._volume = 1.0
        self._speed = 1.0
        self._pitch = 1000
        self.pitch_d = 0
        self.skip_votes = set()

        self.audio_player = rinko.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, value: float):
        self._speed = value

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, value: float):
        self._pitch = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()
            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.queue.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())
            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.queue.clear()
        if self.voice:
            await self.voice.disconnect()
            self.voice = None