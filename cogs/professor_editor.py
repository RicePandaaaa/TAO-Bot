import discord, csv, os
from discord.ext import commands
from discord.ext.commands import Context


class ProfEditor(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_professors(self, ctx: Context, 
                             class_name: str = commands.parameter(description="Name of the class to change (case-sensitive)"),
                             prof_names: str = commands.parameter(description="List of all professor names, separated with only commas")):
        pass


async def setup(bot):
    await bot.add_cog(ProfEditor(bot))
