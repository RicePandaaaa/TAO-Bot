import discord, csv
from discord.ext import commands
from datetime import datetime, timezone, timedelta

class OfficeHours(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.file_name = "cogs/pt_hours.csv"
        self.pts = {}

        

async def setup(bot):
    await bot.add_cog(OfficeHours(bot))
