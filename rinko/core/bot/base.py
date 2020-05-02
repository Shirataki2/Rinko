import discord
from discord.ext import commands

import logging
import asyncio
import aiomysql
import glob
import os
from aiohttp import ClientSession
from typing import Dict, List, Tuple, Any, Union


import rinko
from rinko.core.config import config
from rinko.core.commands.help import CustomHelpCommand
from rinko.core.logger import get_module_logger

logger = get_module_logger(__name__)
class RinkoBase(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(help_command=CustomHelpCommand(), *args, **kwargs)
        self._session = None
        self.metadata_loop = None
        self.startup()
        self.get_all_cogs()

    async def setup_db(self):
        try:
            logger.debug(f'MySQLと接続しています...')
            logger.debug(f'\t{config.mysql_user} {config.mysql_host}:3306/{config.mysql_db}')
            return await aiomysql.create_pool(
                host=config.mysql_host,
                user=config.mysql_user,
                password=config.mysql_passwd,
                autocommit=True,
                db=config.mysql_db,
                cursorclass=aiomysql.DictCursor,
                loop=self.loop,
            )
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error('MySQLサーバとの接続に失敗しました')
            raise e

    def _set_loglevel(self):
        logging_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        if config.log_level in logging_levels:
            logger.info(f"ログレベルを{config.log_level}に設定しました")
            logger.setLevel(logging_levels[config.log_level])
        else:
            logger.warning(f"ログレベル{config.log_level}が見つかりません")
            logger.warning(f"ログレベルをデフォルトのWARNINGに設定します")
            logger.setLevel(logging.WARNING)

    def get_all_cogs(self, reload=False):
        dirname = os.path.dirname(os.path.abspath(__file__))
        cogs = glob.glob(f'{dirname}/../../{config.cog_folder}/**.py')
        logger.debug(f"{'Rel' if reload else 'L'}oading Cogs...")
        for cog in cogs:
            cogname = os.path.basename(os.path.splitext(cog)[0])
            modulename = f'rinko.{config.cog_folder}.{cogname}'
            try:
                if reload:
                    self.reload_extension(modulename)
                else:
                    self.load_extension(modulename)
                logger.debug(f'\t{modulename} ... OK')
            except Exception as e:
                logger.error(f'\t{modulename} ... NG')
                raise e

    async def on_ready(self):
        logger.info("Ready.")
        logger.info("Bot Name : %s", self.user)
        logger.info("Bot  ID  : %s", self.user.id)
        await self.change_presence(status=discord.Status.online)

    def run(self, *args, **kwargs):
        self.pool = self.loop.run_until_complete(self.setup_db())
        try:
            self.loop.run_until_complete(self.start(config.bot_token))
        except KeyboardInterrupt:
            pass
        except discord.LoginFailure:
            logger.critical("tokenが不正です")
        except Exception:
            logger.critical("Error!", exc_info=True)
        finally:
            self.loop.run_until_complete(self.logout())
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
            try:
                self.loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self.loop)))
            except asyncio.CancelledError:
                logger.debug("All pending tasks has been cancelled.")
            finally:
                self.loop.run_until_complete(self.session.close())
                logger.error(" - Shutting down bot - ")

    async def __async_set(self, sql, args):
        await self.wait_until_ready()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
            await conn.commit()

    async def __async_get(self, sql, args) -> Tuple[Dict[str, Any]]:
        await self.wait_until_ready()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                results = await cur.fetchall()
            await conn.commit()
        return results

    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command"""
        if isinstance(error, commands.MissingRequiredArgument):
            logger.info('Missing Required Argument Error')
            title = '🥺 Missing a required argument'
        elif isinstance(error, commands.CommandOnCooldown):
            logger.info('Missing a required argument')
            title = '🔥 Command is on cooldown'
        elif isinstance(error, commands.BadArgument):
            logger.info(f'Bad Argument Error: {ctx.guild.id}')
            title = '😵 Bad argument'
        elif isinstance(error, commands.MissingRequiredArgument):
            logger.info(f'Missing Argument Error: {ctx.guild.id}')
            title = '🥴 Missing argument'
        elif isinstance(error, commands.NotOwner):
            logger.warning(f'Not Owner Error: {ctx.guild.id}')
            title = '🚫 You aren\'t the owner of the bot'
        elif isinstance(error, commands.MissingPermissions):
            logger.warning(f'Permission Error: {ctx.guild.id}')
            title = '🚫 You don\'t have the necessary permissions'
        elif isinstance(error, commands.CommandNotFound):
            logger.info(f'Command Not Found Error: {ctx.guild.id}')
            return
        elif isinstance(error, discord.Forbidden):
            logger.info(f'403 Error: {ctx.guild.id}')
            title = '🚫 403: You don\'t have permission to access the specified resource.'
            return
        elif isinstance(error, commands.CommandInvokeError):
            logger.error('Invoke error')
            title = '😔 Runtime Error'
            embed = discord.Embed(title=f'**{title}**', description=str(error.original),
                                            color=0xff0000)
            await ctx.send(embed=embed)
            raise error.original
        else:
            title = 'Unspecified error'
        embed = discord.Embed(title=f'**{title}**', description=str(error), color=0xff0000)
        await ctx.send(embed=embed)
        raise error

    async def set(self, sql, args=None):
        await self.__async_set(sql, args)
        # self.loop.run_until_complete(self.__async_set(sql, args))

    async def get(self, sql, args=None):
        return await self.__async_get(sql, args)
        #return self.loop.run_until_complete(self.__async_get(sql, args))

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession(loop=self.loop)
        return self._session


    def startup(self):
        logger.info('=*'*29 + '=')
        logger.info('')
        logger.info("     ***** ***                         *                   ")
        logger.info("  ******  * **    *                  **                    ")
        logger.info(" **   *  *  **   ***                 **                    ")
        logger.info("*    *  *   **    *                  **                    ")
        logger.info("    *  *    *                        **            ****    ")
        logger.info("   ** **   *    ***     ***  ****    **  ***      * ***  * ")
        logger.info("   ** **  *      ***     **** **** * ** * ***    *   ****  ")
        logger.info("   ** ****        **      **   ****  ***   *    **    **   ")
        logger.info("   ** **  ***     **      **    **   **   *     **    **   ")
        logger.info("   ** **    **    **      **    **   **  *      **    **   ")
        logger.info("   *  **    **    **      **    **   ** **      **    **   ")
        logger.info("      *     **    **      **    **   ******     **    **   ")
        logger.info("  ****      ***   **      **    **   **  ***     ******    ")
        logger.info(" *  ****    **    *** *   ***   ***  **   *** *   ****     ")
        logger.info("*    **     *      ***     ***   ***  **   ***             ")
        logger.info("*                                                          ")
        logger.info(" **                                                        ")
        logger.info(f"{'v' + rinko.__version__:^59}")
        logger.info('=*'*29 + '=')
