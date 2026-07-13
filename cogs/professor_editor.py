import typing

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
        """ Replaces the professor list for a class (takes effect the next time a prof prompt is posted) """

        names = [name.strip() for name in prof_names.split(",") if name.strip() and name.strip() != "TBD"]

        if not names:
            await ctx.send("Please provide at least one professor name!")
            return

        await self.bot.db.set_professors(class_name, names)
        await ctx.send(f"The professors list for \"{class_name}\" has been set to \"{', '.join(names)}\"! "
                       f"Remember to re-post the prof prompt with `send_prof_prompt` for the changes to show.")

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def list_professors(self, ctx: Context,
                              class_name: typing.Optional[str] = commands.parameter(default=None, description="Name of the class (omit to list all classes)")):
        """ Lists the professors configured for a class, or all classes if none is given """

        if class_name is None:
            classes = await self.bot.db.all_classes()
            if not classes:
                await ctx.send("No classes have professors configured yet!")
                return

            lines = []
            for name in classes:
                professors = await self.bot.db.get_professors(name)
                lines.append(f"- **{name}**: {', '.join(professors)}")
            await ctx.send("\n".join(lines))
            return

        professors = await self.bot.db.get_professors(class_name)
        if not professors:
            await ctx.send(f"There are no professors configured for \"{class_name}\"!")
            return

        await ctx.send(f"Professors for **{class_name}**: {', '.join(professors)}")


async def setup(bot):
    await bot.add_cog(ProfEditor(bot))
