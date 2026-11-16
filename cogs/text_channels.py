import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

class TextChannels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name = "verifyupdate", description = "Update the PT/Prof verification information for the email, user_id, and name of who to contact")
    @app_commands.describe(email = "Official TAMU Email address to contact (**** @tamu.edu).",
                           user = "The mention of the officer who will be contacted from the email.",
                           name = "The name of the officer who will be contacted.")
    @commands.has_any_role("TAO Officer")
    async def update_verification(self, ctx : commands.context,
                                  name : str = commands.parameter(default = None, 
                                                                  description = "The name of the officer who will be contacted."),
                                  user: discord.Member = commands.parameter(default = None, 
                                                                            description = "The mention of the officer who will be contacted from the email."),
                                  email : str = commands.parameter(default = None, 
                                                                   description = "Official TAMU Email address to contact (**** @tamu.edu).")):
        """Update the PT/Prof verification information for the email, user_id, and name of who to contact"""

        if (email is None) or (user is None) or (name is None):
            await ctx.send("You must specify all fields.", ephemeral=True)
            return
        
        if not (email.lower().endswith("@tamu.edu")):
            await ctx.send("You must specify an official TAMU email.", ephemeral=True)
            return
        
        await self.bot.db.set_config("verify_name", name)
        await self.bot.db.set_config("verify_user_id", str(user.id))
        await self.bot.db.set_config("verify_email", email)

        await ctx.send(f"Changed PT/Prof Verification information to {name} ({user.mention}), email: {email}! "
                       f"Re-send the verification prompt for the change to show.", ephemeral = False)


    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_verification_prompt(self, ctx: Context):
        """ Sends the prompt for faculty to verify themselves with the club """

        verify_name = await self.bot.db.get_config("verify_name", "N/A")
        verify_user_id = await self.bot.db.get_config("verify_user_id", "N/A")
        verify_email = await self.bot.db.get_config("verify_email", "N/A")

        # Field contents
        fields = {
            "Overview": "In order to be a verified PT (for ENGR 102 or ENGR/PHYS 216/217) or faculty member and to represent yourself as such, " \
                        "please follow the instructions below for verification!",
            "For PTs": "Please send an email to `"+verify_email+"` (this email belongs to <@"+verify_user_id+">) with the following information:" \
                       "\n- What classes you PT for (include course, section number, and professor's name such as PHYS 216 504 Prof. White or ENGR 102 522 Dr. Ritchey)" \
                       "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\"",
            "For Faculty": "Please send an email to `"+verify_email+"` (this email belongs to <@"+verify_user_id+">) with the following information:" \
                           "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\".",
            "Subject Line and Response Time": "You must send the email from your TAMU email!!! Also, please put something along the lines of \"PT Verification\" or \"Faculty Verification\" " \
                           "in the email subject line so that <@"+verify_user_id+"> can more easily find your email. They will reply back to you within 24 hours: if not, " \
                           "feel free to re-send the email or message them in Discord.",
            "Verification Status": "If "+verify_name+" is unable to verify you from your TAMU email with the following information, They will email you back asking for additional information or for you to re-send corrected information." \
                                   "\n\nIf they are able to verify you, then you will be granted the following roles:" \
                                   "\n- The \"PT\" role and course specific PT role (for PTs)" \
                                   "\n- The \"Prof\" role (for faculty)" \
                                   "\n- Roles for your class (for PTs and faculty that teach ENGR 102 or ENGR/PHYS 216/217)"
        }

        # Make the embed
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="PT and Faculty Verification")

        # Add the fields
        for field_name in fields:
            embed.add_field(name=field_name, value=fields[field_name], inline=False)

        # Send the embed
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TextChannels(bot))