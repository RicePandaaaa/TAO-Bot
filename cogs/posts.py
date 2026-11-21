import discord
from discord import app_commands
from discord.ext import commands

from checks import OFFICER_PERMISSIONS, is_officer
from DiscordSelect import PINGS, PRONOUN_ROLES_KEY, PingsSelect, PronounsSelect, StudentSelect
from utils import link_embed, reply


async def post_in_channel(interaction: discord.Interaction, content: str | None = None, **kwargs) -> None:
    """
    Posts a prompt as the public response to the command. Discord shows "X used /post ..." above it,
    which also visually separates the prompts from each other in the channel.
    """
    await reply(interaction, content, ephemeral=False, **kwargs)


class Posts(commands.Cog):
    """ /post: sends the role menus and info prompts into the current channel """

    post = app_commands.Group(name="post", description="Post a role menu or info prompt in this channel",
                              default_permissions=OFFICER_PERMISSIONS, guild_only=True, extras={"audience": "officer"})

    def __init__(self, bot):
        self.bot = bot

    @post.command(name="welcome")
    @is_officer()
    @app_commands.describe(doing_etam="Role for those still in the ETAM process",
                           done_with_etam="Role for those who have completed the ETAM process",
                           visiting="Role for those just visiting the server",
                           alumni="Role for alumni")
    async def welcome(self, interaction: discord.Interaction, doing_etam: discord.Role, done_with_etam: discord.Role,
                      visiting: discord.Role, alumni: discord.Role) -> None:
        """ Posts the welcome message with the student status menu """

        view = discord.ui.View(timeout=None)
        view.add_item(StudentSelect([doing_etam.id, done_with_etam.id, visiting.id, alumni.id]))

        await post_in_channel(interaction,
                              "Welcome to the TAO server! If you have not already, please **read the newcomer tips at "
                              "<#1144274416965013565> and the server guidelines at <#1023087608928153681>**. Also, please select what type of student you are "
                              "(you can change this later by picking a different option).", view=view)

    @post.command(name="pronouns")
    @is_officer()
    @app_commands.describe(she_her="Role for she/her", he_him="Role for he/him", they_them="Role for they/them",
                           any_pronouns="Role for any pronouns", other_pronouns="Role for other pronouns")
    async def pronouns(self, interaction: discord.Interaction, she_her: discord.Role, he_him: discord.Role,
                       they_them: discord.Role, any_pronouns: discord.Role, other_pronouns: discord.Role) -> None:
        """ Posts the pronouns menu """
        assert interaction.guild is not None

        role_ids = [she_her.id, he_him.id, they_them.id, any_pronouns.id, other_pronouns.id]

        # Stored so the menu still knows its roles after a restart (they don't fit in the custom_id)
        await self.bot.db.set_config(PRONOUN_ROLES_KEY, ",".join(str(role_id) for role_id in role_ids))

        view = discord.ui.View(timeout=None)
        view.add_item(PronounsSelect(interaction.guild.id, role_ids))
        await post_in_channel(interaction, "Select your pronouns!", view=view)

    @post.command(name="pings")
    @is_officer()
    @app_commands.describe(announcements="Server/TAO club announcements role",
                           bulletin_board="Bulletin board announcements role",
                           review="TAO review role")
    async def pings(self, interaction: discord.Interaction, announcements: discord.Role,
                    bulletin_board: discord.Role, review: discord.Role) -> None:
        """ Posts the menu for opting in and out of announcement and TAO review pings """

        lines = "\n".join(f"- **{label}**: {description}" for label, description in PINGS)
        message = (f"Choose which pings you'd like to get:\n{lines}\n\n"
                   f"Select **every** ping you want. Any ping you leave unselected is removed, "
                   f"and picking **--- CLEAR ROLES ---** removes them all.")

        view = discord.ui.View(timeout=None)
        view.add_item(PingsSelect([announcements.id, bulletin_board.id, review.id]))
        await post_in_channel(interaction, message, view=view)

    @post.command(name="verification")
    @is_officer()
    async def verification(self, interaction: discord.Interaction) -> None:
        """ Posts how PTs and faculty get verified (change the contact with /config verification) """

        verify_name = await self.bot.db.get_config("verify_name", "N/A")
        verify_user_id = await self.bot.db.get_config("verify_user_id", "N/A")
        verify_email = await self.bot.db.get_config("verify_email", "N/A")

        embed = link_embed("PT and Faculty Verification", {
            "Overview": "In order to be a verified PT (for ENGR 102 or ENGR/PHYS 216/217) or faculty member and to represent yourself as such, "
                        "please follow the instructions below for verification!",
            "For PTs": "Please send an email to `" + verify_email + "` (this email belongs to <@" + verify_user_id + ">) with the following information:"
                       "\n- What classes you PT for (include course, section number, and professor's name such as PHYS 216 504 Prof. White or ENGR 102 522 Dr. Ritchey)"
                       "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\"",
            "For Faculty": "Please send an email to `" + verify_email + "` (this email belongs to <@" + verify_user_id + ">) with the following information:"
                           "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\".",
            "Subject Line and Response Time": "You must send the email from your TAMU email!!! Also, please put something along the lines of \"PT Verification\" or \"Faculty Verification\" "
                                              "in the email subject line so that <@" + verify_user_id + "> can more easily find your email. They will reply back to you within 24 hours: if not, "
                                              "feel free to re-send the email or message them in Discord.",
            "Verification Status": "If " + verify_name + " is unable to verify you from your TAMU email with the following information, They will email you back asking for additional information or for you to re-send corrected information."
                                   "\n\nIf they are able to verify you, then you will be granted the following roles:"
                                   "\n- The \"PT\" role and course specific PT role (for PTs)"
                                   "\n- The \"Prof\" role (for faculty)"
                                   "\n- Roles for your class (for PTs and faculty that teach ENGR 102 or ENGR/PHYS 216/217)",
        })
        await post_in_channel(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(Posts(bot))
