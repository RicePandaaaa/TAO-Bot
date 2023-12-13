import discord, csv
from discord.ext import commands
from discord.ext.commands import Context


class TextChannels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_rules(self, ctx: Context):
        """ Command for bot to send out all TAO server rules """

        # Embed fields
        links = {
                "TA & PT Guidelines": "https://engineering.tamu.edu/cse/academics/peer-teachers/rules-logistics.html",
                "Student Rules": "https://student-rules.tamu.edu/",
                "Student Handbook": "https://student-rules.tamu.edu/aggiecode/",
                "Discord Code of Conduct": "https://discord.com/guidelines",
                }
        rules = {
                "Overview": "It is expected that all members of this server abide by policies set by TAMU and Discord within this server!" \
                            "The relevant PT and student code of conduct links can be found above. By participating in this server, you agree " \
                            "to obey the rules and guidelines that govern this server.",
                "Treating PTs": "PTs are students as well and have classes. Therefore, please be respectful if a PT is unavailable or must" \
                                " leave when outside of their working hours!",
                "Discussions about Grades": "Questions about why you got the grade you got and similar discussions must be conducted privately " \
                                            "with one of your PTs or your professor through standard means of communication (email, office hours, in-person).",
                "Academic Integrity": "It is expected that everyone upholds the Aggie Honor Code and will refrain from any sort of discussion that may be viewed" \
                                      " as academic dishonesty or a violation of the Aggie Honor Code. This also means that discussing about exam " \
                                      "specifics involving students and revealing code for graded assignments are forbidden in this server.",
                "Staff Guidelines and Interactions": "All PTs, Head PTs, TAMU faculty, and VIPs are expected to be respectful and be mindful that they are" \
                                                     " all in positions of power. Student-staff interactions are encouraged, but please be aware of common " \
                                                     "sense boundaries.",
                }
        nicknames = {
                "PTs": "Current PTs must have at this format: \"<firstName> | PT\". Including last name, year, and major are all optional.",
                "Head PTs": "Current PTs must have at this format: \"<firstName> | Head PT\". Including last name, year, and major are all optional. ",
                "VIPs": "Current PTs must have at this format: \"<firstName> | VIP\". Including last name, year, and major are all optional. ",
                "TAMU Faculty": "Please name yourself such that students can easily identify you!",
                "Students and Former Staff": "For everyone else, any nickname is acceptable as long as it obeys all codes of conduct and does not " \
                                             "reasonably seem as an attempt to impersonate TAMU faculty (including PTs) or an officer of TAO. "
                }
        role_select = {
                "Channel": "https://discord.com/channels/1022962971607060540/1142107250366889985",
                "Choosing Channels": "Please go to the above channel to choose your roles and gain access to the rest of the server!"
        }

        # Match embeds to set of fields
        embed_map ={"Code of Conduct Links": links, 
                    "Server Rules":          rules, 
                    "Nickname Guidelines":   nicknames, 
                    "Selecting Roles":       role_select}
 
        # Make each embed
        for embed_title in embed_map:
            embed = discord.Embed(color=discord.Color.dark_red())
            embed.set_author(name=embed_title)

            # Add the fields
            fields = embed_map[embed_title]
            for field_name in fields:
                embed.add_field(name=field_name, value=fields[field_name], inline=False)

            # Send the embed
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextChannels(bot))