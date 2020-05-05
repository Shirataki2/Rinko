import discord
from discord.ext import commands

import logging
import asyncio
import aiofiles
import glob
import re
import sys
import random
import shutil
import os
import httpx

from time import perf_counter
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

class Command(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot

    @commands.command()
    @commands.cooldown(1, 1)
    async def run(self, ctx: commands.Context, *, code):
        '''
        Run the source code.

        The source code should be written with the markdown syntax as follows.

        $run
        \```python
        print('Hello World')
        \```

        To receive stdin, write two code blocks like the following.
        $run
        \```python
        print(sum(map(int, input().split())))
        \```
        \```
        5 8 13 21
        \```

        The images in the /images folder are returned as a reply.

        __The source code is executed on the Docker container under the following constraints.__

        **1.** The executable languages are C++(GCC 9), Python(3.8), Ruby(2.7), Haskell(GHC 8.8), Rust(Rustc 1.43), Javascript(node 14), PHP(7.4), Go(1.14), Java(Open JDK 14), Shell Script(Bash or Zsh)

        **2.** The maximum compile time is 20 seconds. The maximum execution time is 5 seconds.

        **3.** The output file size limit is 5MB.

        **4.** The number of available processes is 64.

        **5.** Network connection is not available.

        **6.** The available memory is 128MB and the swap memory is 256MB.

        **7.** The number of characters that can be output to discord is 2000, and the number of lines is 30.
        '''
        if sources := re.findall(r'```(.+?)\n(.*?)```', code, re.RegexFlag.DOTALL):
            # stdin check
            os.makedirs(f'{os.path.dirname(sys.argv[0])}/../run/src', exist_ok=True)
            os.makedirs(f'{os.path.dirname(sys.argv[0])}/../run/images', exist_ok=True)
            os.makedirs(f'{os.path.dirname(sys.argv[0])}/../run/media', exist_ok=True)
            try:
                if sources2 := re.findall(r'```(.+?)\n(.*?)```.*?```\n(.*?)```', code, re.RegexFlag.DOTALL):
                    lang, source, stdin = sources2[0]
                    async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/stdin', 'w') as f:
                        await f.write(stdin.strip('\n'))
                else:
                    raise Exception()
            except:
                lang, source = sources[0]
                stdin = ''
                async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/stdin', 'w') as f:
                    await f.write('')
            if attach := ctx.message.attachments:
                try:
                    url = attach[0].url
                    async with httpx.AsyncClient() as client:
                        r = await client.get(url)
                    i:Image.Image = Image.open(BytesIO(r.content))
                    i.save(f'{os.path.dirname(sys.argv[0])}/../run/media/0.png')
                    os.rename(f'{os.path.dirname(sys.argv[0])}/../run/media/0.png', f'{os.path.dirname(sys.argv[0])}/../run/media/0')
                except KeyboardInterrupt:
                    pass
            logger.info(f'Execute by Guild: {ctx.guild.id}')
            pipe = asyncio.subprocess.PIPE
            docker_cmd = await self.get_docker_cmd(lang, source)
            logger.info('Docker Container creating...')
            start = perf_counter()
            proc = await asyncio.create_subprocess_shell(docker_cmd, stdout=pipe, stderr=pipe, loop=self.rinko.loop, limit=2**20)
            out, err = await proc.communicate()
            end = perf_counter()
            elps = end - start
            logger.info(f'Successfully Executed!: {elps:.3f}s')
            stdout = None
            stderr = None
            if err and out:
                await ctx.message.add_reaction('⚠️')
                stdout = out.decode().split('\n')
                stderr = err.decode().split('\n')
            elif err:
                await ctx.message.add_reaction('❌')
                stderr = err.decode().split('\n')
            elif out:
                await ctx.message.add_reaction('✅')
                stdout = out.decode().split('\n')
            else:
                await ctx.message.add_reaction('✅')
                await ctx.send("No stdout")
            async def send(ctx, message, pre):
                if len(message) > 30:
                    message = message[:30]
                    message.append('...')
                message = '\n'.join(message)
                if len(message) > 1950:
                    message = message[:1950]
                    message += '\n...'
                await ctx.send(f'{pre}```\n{message}\n```')
            if stdout:
                await send(ctx, stdout, '**stdout**\n')
            if stderr:
                await send(ctx, stderr, '**stderr**\n')
            images = glob.glob('/root/discord-dev/run/images/**.png')
            images.extend(glob.glob(f'{os.path.dirname(sys.argv[0])}/../run/images/**.jpg'))
            images.extend(glob.glob(f'{os.path.dirname(sys.argv[0])}/../run/images/**.gif'))
            images.extend(glob.glob(f'{os.path.dirname(sys.argv[0])}/../run/images/**.jpeg'))
            if images:
                for i, image in enumerate(sorted(images)[:4]):
                    embed = discord.Embed(title=f'Generated Image {i+1}:')
                    ext = os.path.splitext(image)[1]
                    file = discord.File(image, filename=f'image{ext}')
                    embed.set_image(url=f'attachment://image{ext}')
                    await ctx.send(file=file, embed=embed)
            # await ctx.send(f'Elapsed Time: **{elps:.3f}**s (Includes compile time.)')
            shutil.rmtree(f'{os.path.dirname(sys.argv[0])}/../run')

    async def get_docker_cmd(self, lang, source):
        lang = lang.lower()
        docker_base = 'docker run -e LANG=C --network none --cpu-period=50000 --cpu-quota=25000 --cpuset-cpus=0 --ulimit fsize=5000000:5000000 --oom-kill-disable --pids-limit=64 --rm -v /root/discord-dev/run/src:/src -v /root/discord-dev/run/images:/images -v /root/discord-dev/run/media:/media -w /src --memory=128m --memory-swap=256m '
        if lang in ['cpp', 'c++']:
            logger.info('Run C++ Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.cpp', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}gcc:9.2 timeout -sKILL 20s bash -c "g++ -std=gnu++03 -O2 Main.cpp;timeout -sKILL 5s ./a.out <stdin"'
        elif lang in ['c']:
            logger.info('Run C Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.c', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}gcc:9.2 timeout -sKILL 20s bash -c "gcc -std=gnu11 -O2 Main.c;timeout -sKILL 5s ./a.out <stdin"'
        elif lang in ['py', 'python']:
            logger.info('Run Python Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.py', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}python_extended:3.8 timeout -sKILL 5s bash -c "cat stdin|python3.8 -B Main.py"'
        elif lang in ['js', 'javascript']:
            logger.info('Run JS Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.js', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}node:14.0 timeout -sKILL 5s bash -c "cat stdin|node Main.js"'
        elif lang in ['rb', 'ruby']:
            logger.info('Run Ruby Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.rb', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}ruby:2.7.1 timeout -sKILL 5s bash -c "cat stdin|ruby --disable-gems ./Main.rb"'
        elif lang in ['hs', 'haskell']:
            logger.info('Run Haskell Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.hs', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}haskell:8.8.3 timeout -sKILL 20s bash -c "ghc -o ./a.out -O2 ./Main.hs >/dev/null;timeout -sKILL 5s ./a.out <stdin"'
        elif lang in ['rs', 'rust']:
            logger.info('Run Rust Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.rs', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}rust:1.43.0 timeout -sKILL 20s bash -c "rustc -O -o ./a.out ./Main.rs >/dev/null;timeout -sKILL 5s ./a.out <stdin"'
        elif lang in ['sh', 'bash', 'zsh', 'shell']:
            logger.info('Run Shell Code')
            ext = 'zsh' if lang == 'zsh' else 'sh'
            bin_ = 'zsh' if lang == 'zsh' else 'bash'
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.{ext}', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}theoldmoon0602/shellgeibot:20200430 timeout -sKILL 5s bash -c "{bin_} Main.{ext} < stdin"'
        elif lang in ['java']:
            logger.info('Run Java Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.java', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}openjdk:14 timeout -sKILL 20s bash -c "javac Main.java;timeout -sKILL 5s java -Xss128M Main <stdin"'
        elif lang in ['go', 'golang']:
            logger.info('Run Go Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.go', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}golang:1.14 timeout -sKILL 20s bash -c "go build -o ./a.out ./Main.go;timeout -sKILL 5s ./a.out <stdin"'
        elif lang in ['php']:
            logger.info('Run PHP Code')
            async with aiofiles.open(f'{os.path.dirname(sys.argv[0])}/../run/src/Main.php', 'w') as f:
                await f.write(source)
                docker_cmd = f'{docker_base}php:7.4 timeout -sKILL 5s bash -c "cat stdin|php Main.php"'
        else:
            raise commands.BadArgument(f'Unsurpported Extension: {lang}')
        return docker_cmd


def setup(bot):
    bot.add_cog(Command(bot))