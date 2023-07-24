import discord, typing, csv
from discord.ext import commands
from discord.ext.commands import Context, Greedy


class OfficeHours(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(OfficeHours(bot))