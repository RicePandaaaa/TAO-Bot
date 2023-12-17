import discord, csv
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
        try:
            with open(f"cogs/{class_name}.csv", "r+") as csv_file:
                print(csv_file.readlines())
                csv_file.writelines([name.strip() + "\n" for name in prof_names.split(",")])

            await ctx.send(f"The professors list for \"{class_name}\" has been set to \"{prof_names}\"!")

        except:
            await ctx.send(f"There is no class named \"{class_name}\".")


async def setup(bot):
    await bot.add_cog(ProfEditor(bot))
