import discord
from discord.ext import commands
from discord.ext.commands import Context


class TAO(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.review_216 = "N/A"
        self.review_217 = "N/A"
        self.review_102 = "N/A"

    @commands.hybrid_command()
    @commands.has_any_role('PT', 'TAO Officer', 'Prof')
    async def ptresources(self, ctx: Context):
        """ Sends an embed with links to useful resources for PTs """

        # Field contents
        fields = {
            "Info for New PTs (Google Doc)": "https://docs.google.com/document/d/1JvCgARe7d32JmA3MvYfoq2PwR3YdfZpuK48feHKUvtk/edit#heading=h.gwwqgp1crfcc",
            "How to Log Hours (Discord Message Chain)": "https://discord.com/channels/1022962971607060540/1143205554362269788/1143936580243968090",
            "216/217 Lab - Helpful Info (Google Slides)": "https://docs.google.com/presentation/d/10ZxiElBy0SsB5s-FwOXpJD-jiORtwtdnGqKG4CxraZE/edit#slide=id.p"
        }

        # Make the embed
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Helpful Resources for PTs!")

        # Add the fields
        for field_name in fields:
            embed.add_field(name=field_name, value=fields[field_name], inline=False)

        # Send the embed
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def links(self, ctx: Context) -> None:
        """ Basic command for obtaining links to the bot """

        # Set up the embed
        embed = discord.Embed(color=discord.Color.random())
        embed.set_author(name="ENGR TAO Links")

        # Add values to embed
        links = {"bento.me":   "https://bento.me/engrtao",
                 "Discord":    "https://tx.ag/taoserver",
                 "YouTube":    "https://www.youtube.com/@engrtao",
                 "Instagram":  "https://instagram.com/tamutao",
                 "LinkedIn":   "https://www.linkedin.com/company/engr-tao/"}   
        
        for key in links.keys():
            embed.add_field(name=key, value=links[key], inline=False)

        # Send the embed
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def taoresources(self, ctx: Context):
        """ Sends an embed with links to TAO materials"""

        # Field contents
        fields = {
            "Reviews and Resources from previous and current semesters can be found in the TAO Drive!": "",
            "TAO Drive": "https://tx.ag/taoreviewdrive",
            "216/217 Lab Helpful Info": "https://docs.google.com/presentation/d/10ZxiElBy0SsB5s-FwOXpJD-jiORtwtdnGqKG4CxraZE/edit#slide=id.p",
            "102 Helpful Info": "In progress!",
            "216 Review (Current Semester)": self.review_216,
            "217 Review (Current Semester)": self.review_217,
            "102 Review (Current Semester)": self.review_102
        }

        # Make the embed
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Resources made by TAO!")

        # Add the fields
        for field_name in fields:
            embed.add_field(name=field_name, value=fields[field_name], inline=False)

        # Send the embed
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_216_review_link(self, ctx: Context,
                           link: str = commands.parameter(description="Link to 216 review resources")):
        """
        Sets the review link for ENGR/PHYS 216 for the current semester
        
        :param str link: Link to 216 review resources
        """

        await ctx.send(f"{ctx.author.name} has changed the ENGR/PHYS 216 review link (for the current semester) from {self.review_216} to {link}!")
        self.review_216 = link

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_102_review_link(self, ctx: Context,
                           link: str = commands.parameter(description="Link to 102 review resources")):
        """
        Sets the review link for ENGR 102 for the current semester
        
        :param str link: Link to 102 review resources
        """

        await ctx.send(f"{ctx.author.name} has changed the ENGR 102 review link (for the current semester) from {self.review_102} to {link}!")
        self.review_102 = link

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_217_review_link(self, ctx: Context,
                           link: str = commands.parameter(description="Link to 217 review resources")):
        """
        Sets the review link for ENGR/PHYS 217 for the current semester
        
        :param str link: Link to 217 review resources
        """

        await ctx.send(f"{ctx.author.name} has changed the ENGR/PHYS review link (for the current semester) from {self.review_217} to {link}!")
        self.review_217 = link

async def setup(bot):
    await bot.add_cog(TAO(bot))
