import discord
from discord.ext import commands, tasks

import logging
import asyncio
import os
import sys
import random
from datetime import datetime

import rinko
from rinko.core.bot.rinko import Rinko
from rinko.core.logger import get_module_logger
from rinko.core.constant import *

logger = get_module_logger(__name__)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.rinko: Rinko = bot
        self.update_turnip.start()
        self.rot_turnip.start()

    async def get_user_wallet(self, guild: discord.Guild, user: discord.User):
        r = await self.rinko.get(f'SELECT * FROM wallet WHERE guild = {guild.id} AND user = {user.id};')
        if r:
            return r[0]
        else:
            return None

    async def earn(self, guild: discord.Guild, user: discord.Member ,reward: int):
        if await self.get_user_wallet(guild, user):
            await self.rinko.set(f'UPDATE wallet SET money = money + {reward} WHERE guild = {guild.id} AND user = {user.id};')
        else:
            await self.rinko.set(f'INSERT INTO wallet (guild, user, money, buy_at, turnip, rotten_turnip) VALUES ({guild.id}, {user.id}, {reward}, NOW(), 0, 0);')

    async def buy_subroutine(self, guild: discord.Guild, user: discord.Member, per_turnip: int, amount: int):
        if wallet := await self.get_user_wallet(guild, user):
            if wallet['money'] > amount * per_turnip:
                await self.rinko.set(f'UPDATE wallet SET money = money - {amount * per_turnip}, turnip = turnip + {amount}, buy_at = NOW() WHERE guild = {guild.id} AND user = {user.id};')
                return True
            else:
                return False
        else:
            return False

    async def sell_subroutine(self, guild: discord.Guild, user: discord.Member, per_turnip: int):
        if wallet := await self.get_user_wallet(guild, user):
            if (amount := wallet['turnip']) > 0:
                await self.rinko.set(f'UPDATE wallet SET money = money + {amount * per_turnip}, turnip = turnip - {amount} WHERE guild = {guild.id} AND user = {user.id};')
                return True
            else:
                return False
        else:
            return False

    async def set_turnip(self, value: float, type: str):
        await self.rinko.set(f'INSERT INTO turnip (price, type, date) VALUES ({value}, "{type}", NOW())')

    async def get_turnip(self):
        if r := await self.rinko.get(f'SELECT * FROM turnip ORDER BY date DESC LIMIT 1'):
            return r[0]
        else:
            return None

    @commands.command()
    async def daily(self, ctx: commands.Context):
        '''
        Earn a reward that you only get once a day!
        '''
        if work := await self.rinko.get(f'SELECT * FROM works WHERE date >= (NOW() - INTERVAL 1 DAY) AND guild = {ctx.guild.id} AND user = {ctx.author.id} ORDER BY date DESC LIMIT 1;'):
            return await ctx.send(f'💴 You\'ve already earned today\'s reward! (at **{work[0]["date"]}**)')
        v = random.randint(500, 1300)
        await self.earn(ctx.guild, ctx.author, v)
        await self.rinko.set(f'INSERT INTO works (guild, user, date) VALUES ({ctx.guild.id}, {ctx.author.id}, NOW());')
        await ctx.send(f'🔔 Here is your daily **{v}** Bells!\n🕛 You can run it again in **24** hours!')

    @commands.command()
    async def bells(self, ctx: commands.Context):
        '''Returns the amount of Bell (fictitious currency) that you currently have.'''
        if wallet := await self.get_user_wallet(ctx.guild, ctx.author):
            return await ctx.send(f'🔔 You currently have **{wallet["money"]}** Bells')
        else:
            return await ctx.send(f'🔔 You currently have **No** Bells')

    @commands.command()
    async def myturnips(self, ctx: commands.Context):
        '''Returns the amount of turnips ("stocks" in "Animal Crossing") that you currently have.'''
        self.emoji = self.rinko.get_emoji(706946880810254436)
        if wallet := await self.get_user_wallet(ctx.guild, ctx.author):
            await ctx.send(f'{self.emoji} You currently have **{wallet["turnip"]}** Turnips (Buy at **{wallet["buy_at"]}**)')
            if wallet["rotten_turnip"] > 0:
                return await ctx.send(f'　　...and **{wallet["rotten_turnip"]}** Rotten Turnips')
        else:
            return await ctx.send(f'{self.emoji} You currently have **No** Turnips')

    @commands.command()
    async def turnips(self, ctx: commands.Context):
        '''Returns the current value of the turnip.'''
        self.emoji = self.rinko.get_emoji(706946880810254436)
        if turnip := await self.get_turnip():
            return await ctx.send(f'{self.emoji} The current price of the turnip is **{turnip["price"]:.4f}**Bell.')
        else:
            return await ctx.send(f'{self.emoji} The current price of the turnip is 0Bell.')

    @commands.command()
    async def buy(self, ctx: commands.Context, amount: int):
        '''
        Buy the number of turnips specified by "amount". (Be careful, they'll rot in three days!)
        You can't buy a stock if you have not sold it.
        '''
        amount = int(amount)
        if amount <= 0:
            return await ctx.send(f'The argument "amount" must be a natural number.')
        self.emoji = self.rinko.get_emoji(706946880810254436)
        turnip = await self.get_turnip()
        m = await self.get_user_wallet(ctx.guild, ctx.author)
        if m.get('turnip') > 0:
            return await ctx.send(f'You already have an old turnip... Sell it all first, then buy it!')
        if await self.buy_subroutine(ctx.guild, ctx.author, turnip["price"], amount):
            m = await self.get_user_wallet(ctx.guild, ctx.author)
            return await ctx.send(f'You bought {amount} turnips!\n 💴: **{m["money"]}**\n {self.emoji}: **{m["turnip"]}**\n 💴 / {self.emoji} = **{turnip["price"]}**')
        else:
            return await ctx.send(f'You don\'t have enough money to buy it!\nYou have **{m["money"] if m else 0}** Bells. But **{amount}** * {self.emoji} **{turnip["price"]}** = **{amount * turnip["price"]}** Bells Needed')

    @commands.command()
    async def sell(self, ctx: commands.Context):
        '''
        Sell all the turnips you own that aren't rotten.
        '''
        self.emoji = self.rinko.get_emoji(706946880810254436)
        turnip = await self.get_turnip()
        m = await self.get_user_wallet(ctx.guild, ctx.author)
        if m.get('turnip') <= 0:
            return await ctx.send(f'Well, apparently, you don\'t have any turnips!')
        if await self.sell_subroutine(ctx.guild, ctx.author, turnip["price"]):
            m2 = await self.get_user_wallet(ctx.guild, ctx.author)
            return await ctx.send(f'You sold {m["turnip"]} turnips and earn **{m["turnip"] * turnip["price"]}** Bells!\n 💴: **{m2["money"]}**\n {self.emoji}: **0**\n 💴 / {self.emoji} = **{turnip["price"]}**')
        else:
            return await ctx.send(f'Well, apparently, you don\'t have any turnips!')


    @tasks.loop(minutes=1)
    async def update_turnip(self):
        if datetime.now().minute in [0, 30]:
            turnip = await self.get_turnip()
            type = turnip['type']
            r = random.random()
            s = random.random()
            if type == 'D':
                if r < 0.17:
                    rate = random.randint(890, 917) / 1000
                elif r < 0.87:
                    rate = random.randint(960, 997) / 1000
                else:
                    rate = random.randint(995, 1038) / 1000
                if datetime.now().hour in [0, 6, 12, 18] and datetime.now().minute == 0:
                    if s < 0.5:
                        type = 'I'
                    elif s < 0.68:
                        type = 'D'
                    elif s < 0.88:
                        type = 'S'
                    elif s < 1:
                        type = 'SS'
            if type == 'I':
                if r < 0.6:
                    rate = random.randint(1008, 1054) / 1000
                elif r < 0.7:
                    rate = random.randint(990, 1003) / 1000
                else:
                    rate = random.randint(905, 954) / 1000
                if datetime.now().hour in [0, 4, 8, 12, 16, 20] and datetime.now().minute == 0:
                    if s < 0.2:
                        type = 'I'
                    elif s < 0.4:
                        type = 'D'
                    elif s < 0.95:
                        type = 'S'
                    elif s < 1:
                        type = 'SS'
            if type == 'S':
                if r < 0.3:
                    rate = random.randint(910, 970) / 1000
                elif r < 0.9:
                    rate = random.randint(1030, 1110) / 1000
                else:
                    rate = random.randint(950, 1050) / 1000
                if datetime.now().hour in [0, 6, 12, 18] and datetime.now().minute == 0:
                    if s < 0.1:
                        type = 'I'
                    elif s < 0.6:
                        type = 'D'
                    elif s < 0.9:
                        type = 'S'
                    elif s < 1:
                        type = 'SS'
            if type == 'SS':
                if r < 0.1:
                    rate = random.randint(994, 1004) / 1000
                elif r < 0.8:
                    rate = random.randint(1060, 1160) / 1000
                else:
                    rate = random.randint(860, 970) / 1000
                if datetime.now().hour in [0, 3, 6, 9, 12, 15, 18, 21] and datetime.now().minute == 0:
                    if s < 0.3:
                        type = 'I'
                    elif s < 0.8:
                        type = 'D'
                    elif s < 0.99:
                        type = 'S'
                    elif s < 1:
                        type = 'SS'
            if turnip['price'] * rate > random.randint(2000, 2050):
                rate = 0.97
            if turnip['price'] * rate < random.randint(50, 70):
                rate = 1.1
            price = turnip['price'] * rate
            await self.set_turnip(price, type)

    @tasks.loop(minutes=1)
    async def rot_turnip(self):
        await self.rinko.set(f'UPDATE wallet SET rotten_turnip = rotten_turnip + turnip WHERE buy_at <= (NOW() - INTERVAL 3 DAY);')
        await self.rinko.set(f'UPDATE wallet SET turnip = 0 WHERE buy_at <= (NOW() - INTERVAL 3 DAY);')


def setup(bot):
    bot.add_cog(Economy(bot))