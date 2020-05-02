from asyncio import TimeoutError, sleep
from datetime import datetime
from os import getcwd
from subprocess import getoutput
from time import perf_counter

from discord import Embed, Colour, errors
from discord.ext import commands, tasks

from rinko.core.constant import *

class CustomHelpCommand(commands.HelpCommand):
    """The custom help command class for the bot"""

    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help about the bot, a command, or a cog\neg. `{prefix}help Steam` (There should be 4 cogs '
                    'and 25 commands)'
        })

    def get_command_signature(self, command):
        """Method to return a commands name and signature"""
        if not command.signature and not command.parent:  # checking if it has no args and isn't a subcommand
            return f'`{self.clean_prefix}{command.name}`'
        if command.signature and not command.parent:  # checking if it has args and isn't a subcommand
            return f'`{self.clean_prefix}{command.name}` `{command.signature}`'
        if not command.signature and command.parent:  # checking if it has no args and is a subcommand
            return f'**╚╡**`{command.name}`'
        else:  # else assume it has args a signature and is a subcommand
            return f'**╚╡**`{command.name}` `{command.signature}`'

    def get_command_aliases(self, command):  # this is a custom written method along with all the others below this
        """Method to return a commands aliases"""
        if not command.aliases:  # check if it has any aliases
            return ''
        else:
            return f'command aliases are [`{"` | `".join([alias for alias in command.aliases])}`]'

    def get_command_description(self, command):
        """Method to return a commands short doc/brief"""
        if not command.short_doc:  # check if it has any brief
            return 'There is no documentation for this command currently'
        else:
            return command.short_doc.format(prefix=self.clean_prefix)

    def get_command_help(self, command):
        """Method to return a commands full description/doc string"""
        if not command.help:  # check if it has any brief or doc string
            return 'There is no documentation for this command currently'
        else:
            return command.help.format(prefix=self.clean_prefix)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot
        page = 0
        cogs = [cog for cog in bot.cogs]
        cogs.sort()

        def check(reaction, user):  # check who is reacting to the message
            return user == ctx.author and help_embed.id == reaction.message.id

        embed = await self.bot_help_paginator(page, cogs)
        help_embed = await ctx.send(embed=embed)  # sends the first help page

        reactions = ('\N{BLACK LEFT-POINTING TRIANGLE}',
                     '\N{BLACK RIGHT-POINTING TRIANGLE}',
                     '\N{BLACK SQUARE FOR STOP}',
                     '\N{INFORMATION SOURCE}')  # add reactions to the message
        bot.loop.create_task(self.bot_help_paginator_reactor(help_embed, reactions))
        # this allows the bot to carry on setting up the help command

        while 1:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60, check=check)  # checks message reactions
            except TimeoutError:  # session has timed out
                try:
                    await help_embed.clear_reactions()
                except errors.Forbidden:
                    pass
                break
            else:
                try:
                    await help_embed.remove_reaction(str(reaction.emoji), ctx.author)  # remove the reaction
                except errors.Forbidden:
                    pass

                if str(reaction.emoji) == '◀':  # go to the previous page
                    page -= 1
                    if page == -1:  # check whether to go to the final page
                        page = len(cogs) - 1
                    embed = await self.bot_help_paginator(page, cogs)
                    await help_embed.edit(embed=embed)
                elif str(reaction.emoji) == '▶':  # go to the next page
                    page += 1
                    if page == len(cogs):  # check whether to go to the first page
                        page = 0
                    embed = await self.bot_help_paginator(page, cogs)
                    await help_embed.edit(embed=embed)

                elif str(reaction.emoji) == 'ℹ':  # show information help
                    all_cogs = '`, `'.join([cog for cog in cogs])
                    embed = Embed(title=f'Help with {bot.user.name}\'s commands', description=bot.description,
                                  color=THEME_COLOR)
                    embed.add_field(
                        name=f'Currently you have {len(bot.cogs)} cogs loaded, which are (`{all_cogs}`) :gear:',
                        value='`<...>` indicates a required argument,\n`[...]` indicates an optional argument.\n\n'
                              '**Don\'t however type these around your argument**')
                    embed.add_field(name='What do the emojis do:',
                                    value=':arrow_backward: Goes to the previous page\n'
                                          ':arrow_forward: Goes to the next page\n'
                                          ':stop_button: Deletes and closes this message\n'
                                          ':information_source: Shows this message')
                    embed.set_author(name=f'You were on page {page + 1}/{len(bot.cogs)} before',
                                     icon_url=ctx.author.avatar_url)
                    embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.',
                                     icon_url=ctx.bot.user.avatar_url)
                    await help_embed.edit(embed=embed)

                elif str(reaction.emoji) == '⏹':  # delete the message and break from the wait_for
                    await help_embed.delete()
                    break

    async def bot_help_paginator_reactor(self, message, reactions):
        for reaction in reactions:
            await message.add_reaction(reaction)

    async def bot_help_paginator(self, page: int, cogs: list):
        ctx = self.context
        bot = ctx.bot
        all_commands = [command for command in
                        await self.filter_commands(bot.commands)]  # filter the commands the user can use
        cog = bot.get_cog(cogs[page])  # get the current cog

        embed = Embed(title=f'Help with {cog.qualified_name} ({len(all_commands)} commands)',
                      description=cog.description, color=THEME_COLOR)
        embed.set_author(name=f'Help ({page + 1}/{len(cogs)})', icon_url=ctx.author.avatar_url)
        for c in cog.walk_commands():
            try:
                if await c.can_run(ctx) and not c.hidden:
                    signature = self.get_command_signature(c)
                    description = self.get_command_description(c)
                    if c.parent:  # it is a sub-command
                        embed.add_field(name=signature, value=description, inline=False)
                    else:
                        embed.add_field(name=signature, value=description, inline=False)
            except:
                pass
        embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.',
                         icon_url=ctx.bot.user.avatar_url)
        return embed

    async def send_cog_help(self, cog):
        ctx = self.context
        cog_commands = [command for command in await self.filter_commands(cog.walk_commands())]  # get commands
        embed = Embed(title=f'Help with {cog.qualified_name} ({len(cog_commands)} commands)',
                      description=cog.description, color=THEME_COLOR)
        embed.set_author(name=f'Help',
                         icon_url=ctx.author.avatar_url)
        for c in cog_commands:
            signature = self.get_command_signature(c)
            aliases = self.get_command_aliases(c)
            description = self.get_command_description(c)
            if c.parent:
                embed.add_field(name=signature, value=description)
            else:
                embed.add_field(name=f'{signature} {aliases}',
                                value=description, inline=False)
        embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.',
                         icon_url=ctx.bot.user.avatar_url)
        await ctx.send(embed=embed)

    async def send_command_help(self, command):
        ctx = self.context
        if await command.can_run(ctx):
            embed = Embed(title=f'Help with `{command.name}`', color=THEME_COLOR)
            embed.set_author(
                name='Help',
                icon_url=ctx.author.avatar_url)
            signature = self.get_command_signature(command)
            description = self.get_command_help(command)
            aliases = self.get_command_aliases(command)

            if command.parent:
                embed.add_field(name=signature, value=description, inline=False)
            else:
                embed.add_field(name=f'{signature} {aliases}', value=description, inline=False)
            embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.')
            await ctx.send(embed=embed)

    async def send_group_help(self, group):
        ctx = self.context
        bot = ctx.bot

        embed = Embed(title=f'Help with `{group.name}`', description=bot.get_command(group.name).help,
                      color=THEME_COLOR)
        embed.set_author(
            name=f'Help',
            icon_url=ctx.author.avatar_url)
        for command in group.walk_commands():
            if await command.can_run(ctx):
                signature = self.get_command_signature(command)
                description = self.get_command_description(command)
                aliases = self.get_command_aliases(command)

                if command.parent:
                    embed.add_field(name=signature, value=description, inline=False)
                else:
                    embed.add_field(name=f'{signature} {aliases}', value=description, inline=False)
        embed.set_footer(text=f'Use "{self.clean_prefix}help <command>" for more info on a command.')
        await ctx.send(embed=embed)

    async def send_error_message(self, error):
        pass

    async def command_not_found(self, string):
        embed = Embed(title='Error!',
                      description=f'**Error 404:** Command or cog "{string}" not found ¯\_(ツ)_/¯',
                      color=Colour.red())
        embed.add_field(name='The current loaded cogs are',
                        value=f'(`{"`, `".join([cog for cog in self.context.bot.cogs])}`) :gear:')
        await self.context.send(embed=embed)