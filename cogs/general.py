import discord, typing
from discord.ext import commands
from discord.ext.commands import Context, Greedy


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.review_216 = "N/A"
        self.review_217 = "N/A"
        self.review_102 = "N/A"

    @commands.hybrid_command()
    @commands.guild_only()
    async def sync(self, ctx: Context) -> None:
        await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send("Commands synced!")

    @commands.hybrid_command()
    @commands.guild_only()
    async def desync(self, ctx: Context) -> None:
        ctx.bot.tree.clear_commands(guild=ctx.guild)
        await ctx.send("Commands desynced!")

    @commands.hybrid_command()
    async def howdy(self, ctx: Context) -> None:
        """ Basic command for obtaining info about the bot """
        
        await ctx.send(f"Howdy <@{ctx.author.id}>, I was created to assist PTs and professors in managing voice channels for one-on-one " \
                        "sessions for students and content reviews. I can also provide students with information " \
                        "related to office hours! Please type `tao.help` for a complete command list!")
        
    @commands.hybrid_command()
    async def code(self, ctx: Context) -> None:
        """ Basic command warning users against posting code for their HW or other assignments """

        await ctx.send(f"Howdy, <@{ctx.author.id}> would like to remind you to **NEVER SHARE ANY PART OF YOUR CODE THAT IS USED IN YOUR SUBMITTED ASSIGNMENTS.**" \
                       " You can only share code that was created for purposes unrelated to your assignments." \
                        " Posting your code used in assignments (such as labs and HW) can and will lead to severe consequences.")

    @commands.hybrid_command()
    async def freshman_information(self, ctx: Context) -> None:
        """ Sends an embed with links to the information for freshmen """

        # Field contents
        fields = {
            "ETAM Information": "https://engineering.tamu.edu/academics/undergraduate/entry-to-a-major/index.html",
            "University Writing Center": "https://writingcenter.tamu.edu/",
            "Academic Success Center": "https://engineering.tamu.edu/academics/academic-support-services.html",
        }

        # Make the embed
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Help Centers")

        # Add the fields
        for field_name in fields:
            embed.add_field(name=field_name, value=fields[field_name], inline=False)

        # Send the embed
        await ctx.send(embed=embed)

   

async def setup(bot):
    await bot.add_cog(General(bot))
