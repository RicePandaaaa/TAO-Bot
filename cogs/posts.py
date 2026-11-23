import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.checks import OFFICER_PERMISSIONS, is_officer
from views.role_menus import PINGS, PRONOUN_ROLES_KEY, PingsSelect, PronounsSelect, StudentSelect
from core.utils import link_embed, reply

DEFAULT_AGREE_EMOJI = "✅"


def same_emoji(a: str, b: str) -> bool:
    """ Compares emojis, ignoring the invisible variation selector some keyboards add (✅ vs ✅️) """
    return a.replace("\ufe0f", "") == b.replace("\ufe0f", "")


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
        # (message ID, role ID, emoji) of the current /post agree message, so reactions don't hit the database
        self.rules: tuple[int, int, str] | None = None

    async def cog_load(self) -> None:
        message_id = await self.bot.db.get_config_id("rules_message_id")
        role_id = await self.bot.db.get_config_id("rules_role")
        emoji = await self.bot.db.get_config("rules_emoji")
        if message_id is not None and role_id is not None and emoji:
            self.rules = (message_id, role_id, emoji)

    # ---------- Agree to the rules ----------

    @post.command(name="agree")
    @is_officer()
    @app_commands.describe(message="The sentence to post, e.g. \"React below to agree to the rules and unlock the server!\"",
                           role="Role members get by reacting (give it access to the server's channels)",
                           emoji=f"Emoji members react with (default {DEFAULT_AGREE_EMOJI})")
    async def agree(self, interaction: discord.Interaction, message: str, role: discord.Role,
                    emoji: str = DEFAULT_AGREE_EMOJI) -> None:
        """ Posts a message members react to, to agree to the rules and get a role that unlocks the server """
        emoji = emoji.strip()

        # Ensure role can be assigned
        if not role.is_assignable():
            await reply(interaction, f"I can't give out {role.mention}. It has to be below my highest role "
                                     f"and can't be @everyone or a bot/integration role.")
            return

        # Check that emote exists natively
        partial = discord.PartialEmoji.from_str(emoji)
        if partial.id is not None and self.bot.get_emoji(partial.id) is None:
            await reply(interaction, f"I can't use {emoji}. Custom emojis have to be from this server.")
            return

        # Send message out
        await post_in_channel(interaction, message)
        posted = await interaction.original_response()

        try:
            await posted.add_reaction(emoji)
        except discord.HTTPException:
            # If the emoji reaction fails, then take down the message and alert user
            await posted.delete()
            await interaction.followup.send(f"\"{emoji}\" isn't an emoji I can react with, so I took the message back down. "
                                            f"Try again with a standard emoji or one from this server.", ephemeral=True)
            return

        # Set the rule info
        old_message_id = self.rules[0] if self.rules is not None else None
        self.rules = (posted.id, role.id, emoji)
        await self.bot.db.set_config("rules_message_id", str(posted.id))
        await self.bot.db.set_config("rules_role", str(role.id))
        await self.bot.db.set_config("rules_emoji", emoji)

        note = (f"Reacting with {emoji} gives {role.mention}, and removing the reaction takes it away. "
                f"Make sure {role.mention} is what lets members see the server's channels.")

        # Double check that the message is valid
        if old_message_id is not None and old_message_id != posted.id:
            note += ("\nThe previous agree message no longer gives the role, so you can delete it. "
                     "Members who already agreed keep the role.")
        await interaction.followup.send(note, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    def rules_role_for(self, payload: discord.RawReactionActionEvent) -> discord.Role | None:
        """ The role to give/take for this reaction, or None if it isn't the agree reaction on the rules """
        if self.rules is None or payload.guild_id is None:
            return None
        message_id, role_id, emoji = self.rules
        if payload.message_id != message_id or not same_emoji(str(payload.emoji), emoji):
            return None
        if self.bot.user is not None and payload.user_id == self.bot.user.id:
            return None

        guild = self.bot.get_guild(payload.guild_id)
        return guild.get_role(role_id) if guild is not None else None

    # Raw events, since the rules message usually isn't in the bot's cache after a restart
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        role = self.rules_role_for(payload)
        member = payload.member
        if role is None or member is None or member.bot or role in member.roles:
            return
        try:
            await member.add_roles(role, reason="Agreed to the rules")
        except discord.HTTPException as error:
            logging.warning(f"Couldn't give {member} the rules role: {error}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        role = self.rules_role_for(payload)
        if role is None:
            return
        member = role.guild.get_member(payload.user_id)
        if member is None or role not in member.roles:
            return
        try:
            await member.remove_roles(role, reason="Removed their rules reaction")
        except discord.HTTPException as error:
            logging.warning(f"Couldn't remove the rules role from {member}: {error}")

    # ---------- Role menus and info prompts ----------

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
                              "Welcome to the TAO server! Please continue looking through the roles below!", view=view)

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
