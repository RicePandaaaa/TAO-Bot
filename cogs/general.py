import discord
import help_content
from help_views import HelpView
from discord.ext import commands
from discord.ext.commands import Context, Greedy
import typing

class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_any_role('TAO Officer')
    async def sync(self, ctx: Context, 
                   guilds: Greedy[discord.Object] = commands.parameter(default=None, description="A list of guilds to go through"), 
                   spec: typing.Optional[typing.Literal["~", "*", "^"]] = commands.parameter(default=None, description="Type of sync to be performed")) -> None:
        """ 
        Syncs the hybrid commands (allows for usage of slash commands), from discord.py server  
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
                print(synced)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
                print(synced)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()
                print(synced)

    @commands.hybrid_command()
    async def help(self, ctx: Context) -> None:
        """Basic command for information on available commands"""

        await ctx.send(
            embed=help_content.help_overview(),
            view=HelpView(),
            ephemeral=True,
        )

    @commands.hybrid_command()
    async def howdy(self, ctx: Context) -> None:
        """ Basic command for obtaining info about the bot """

        await ctx.send(embed=help_content.howdy_card(ctx.author.id))
    
    @commands.hybrid_command()
    async def code(self, ctx: Context) -> None:
        """ Basic command warning users against posting code for their HW or other assignments """

        await ctx.send(embed=help_content.code_card(ctx.author.id))

    @commands.hybrid_command()
    async def freshman_information(self, ctx: Context) -> None:
        """ Sends an embed with links to the information for freshmen """

        await ctx.send(embed=help_content.freshman_information_card())
    
    @commands.hybrid_command()
    async def mental_health_resources(self, ctx: Context) -> None:
        """ Sends an embed with links to mental health resources """

        await ctx.send(embed=help_content.mental_health_resources_card())

   

async def setup(bot):
    await bot.add_cog(General(bot))
