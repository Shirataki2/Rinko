import discord
from discord.ext import commands

import logging
import asyncio
import glob
import os

from aiohttp import ClientSession

import rinko
from rinko.core.config import config
from rinko.core.logger import get_module_logger

logger = get_module_logger(__name__)

class EmbedPaginator(commands.Paginator):
    def __init__(self, **kwargs):
        super().__init__()
        self.template = None
        self.splitter = "#=SPL=#"
        self.lines = []

    def append(self, line=''):
        self.lines.append(line)

    def newpage(self):
        self.lines.append(self.splitter)

    def add_template(self, embed):
        self.template = embed

    async def paginate(self, ctx: commands.Context, footer_text=None):
        current_page = 0
        pages = [line.replace(self.splitter, "") for line in "\n".join(self.lines).split(f"\n{self.splitter}\n")]
        if self.template:
            embed = self.template
        else:
            embed = discord.Embed()
        embed.description = pages[current_page]
        if len(pages) <= 1:
            logger.debug("1ページのみのためPaginationはしません")
            return await ctx.send(embed=embed)
        else:
            if footer_text:
                embed.set_footer(text=f"{footer_text} (Page {current_page + 1}/{len(pages)})")
            else:
                embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
            logger.debug("1ページ目を送信...")
            message = await ctx.send(embed=embed)
            emojis = ("\u23EE", "\u2B05", "\u23F9", "\u27A1", "\u23ED")
        for emoji in emojis:
            # Add all the applicable emoji to the message
            logger.debug(f"Adding reaction: {repr(emoji)}")
            await message.add_reaction(emoji)
        def event_check(reaction_: discord.Reaction, user_: discord.Member) -> bool:
            """Make sure that this reaction is what we want to operate on."""
            no_restrictions = (
                not restrict_to_user
                or user_.id == restrict_to_user.id
            )
            return (
                # Conditions for a successful pagination:
                all((
                    # Reaction is on this message
                    reaction_.message.id == message.id,
                    # Reaction is one of the pagination emotes
                    str(reaction_.emoji) in emojis,
                    # Reaction was not made by the Bot
                    user_.id != ctx.bot.user.id,
                    # There were no restrictions
                    no_restrictions
                ))
            )
        while True:
            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", timeout=120, check=event_check)
                logger.debug(f"Reaction: {reaction}")
            except asyncio.TimeoutError:
                logger.debug("Timoout")
                break  # We're done, no reactions for the last 5 minutes
            if str(reaction.emoji) == emojis[2]:
                logger.debug("Got delete reaction")
                return await message.delete()
            if reaction.emoji == emojis[0]:
                await message.remove_reaction(reaction.emoji, user)
                current_page = 0
                logger.debug(f"Got first page reaction - changing to page 1/{len(pages)}")
                embed.description = ""
                await message.edit(embed=embed)
                embed.description = pages[current_page]
                if footer_text:
                    embed.set_footer(text=f"{footer_text} (Page {current_page + 1}/{len(pages)})")
                else:
                    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
            if reaction.emoji == emojis[4]:
                await message.remove_reaction(reaction.emoji, user)
                current_page = len(pages) - 1
                logger.debug(f"Got last page reaction - changing to page {current_page + 1}/{len(pages)}")
                embed.description = ""
                await message.edit(embed=embed)
                embed.description = pages[current_page]
                if footer_text:
                    embed.set_footer(text=f"{footer_text} (Page {current_page + 1}/{len(pages)})")
                else:
                    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
            if reaction.emoji == emojis[1]:
                await message.remove_reaction(reaction.emoji, user)
                if current_page <= 0:
                    logger.debug("Got previous page reaction, but we're on the first page - ignoring")
                    continue
                current_page -= 1
                logger.debug(f"Got previous page reaction - changing to page {current_page + 1}/{len(pages)}")
                embed.description = ""
                await message.edit(embed=embed)
                embed.description = pages[current_page]
                if footer_text:
                    embed.set_footer(text=f"{footer_text} (Page {current_page + 1}/{len(pages)})")
                else:
                    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
            if reaction.emoji == emojis[3]:
                await message.remove_reaction(reaction.emoji, user)
                if current_page >= len(pages) - 1:
                    logger.debug("Got next page reaction, but we're on the last page - ignoring")
                    continue
                current_page += 1
                logger.debug(f"Got next page reaction - changing to page {current_page + 1}/{len(pages)}")
                embed.description = ""
                await message.edit(embed=embed)
                embed.description = pages[current_page]
                if footer_text:
                    embed.set_footer(text=f"{footer_text} (Page {current_page + 1}/{len(pages)})")
                else:
                    embed.set_footer(text=f"Page {current_page + 1}/{len(pages)}")
                await message.edit(embed=embed)
        logger.debug("Ending pagination and clearing reactions.")
        with suppress(discord.NotFound):
            await message.clear_reactions()