import typing

import discord
from discord import app_commands
from discord.ext import commands

from checks import OFFICER_PERMISSIONS, PT_ROLE, is_officer
from utils import reply
from views.confirm import ConfirmView

MAX_NICKNAME_LENGTH = 32
PT_SUFFIX = " | PT"


class PT(commands.Cog):
    """ /pt: giving out PT roles and moving everyone between semesters """

    pt = app_commands.Group(name="pt", description="Give PT roles and switch PT roles between semesters",
                            default_permissions=OFFICER_PERMISSIONS, guild_only=True, extras={"audience": "officer"})

    def __init__(self, bot):
        self.bot = bot

    @pt.command(name="add")
    @is_officer()
    @app_commands.describe(member="The member who is becoming a PT",
                           class_role="Their class-specific PT role",
                           real_name="Their real name, used for the nickname \"<name> | PT\" (optional)")
    async def add(self, interaction: discord.Interaction, member: discord.Member, class_role: discord.Role,
                  real_name: typing.Optional[str] = None) -> None:
        """ Gives a member the PT role and a class PT role, and sets their nickname """
        assert interaction.guild is not None
        await interaction.response.defer(ephemeral=True, thinking=True)

        roles = [class_role]
        pt_role = discord.utils.get(interaction.guild.roles, name=PT_ROLE)
        if pt_role is not None:
            roles.append(pt_role)
        await member.add_roles(*[role for role in roles if role not in member.roles], reason=f"Made a PT by {interaction.user}")

        notes = []
        if pt_role is None:
            notes.append(f"There is no \"{PT_ROLE}\" role in this server, so only {class_role.mention} was given.")

        if real_name is not None:
            # Trim the name so the nickname stays within Discord's limit
            name = real_name.strip()[:MAX_NICKNAME_LENGTH - len(PT_SUFFIX)].rstrip()
            try:
                await member.edit(nick=f"{name}{PT_SUFFIX}")
            except discord.Forbidden:
                # Discord never lets bots rename the server owner or members above the bot's role
                notes.append("I couldn't change their nickname (they're the server owner or above my role).")

        notes.append("Remember to manually give them their professor roles if they should have any!")
        await reply(interaction, f"{member.mention} is now a PT.\n" + "\n".join(notes))

        # Log the change in the bot-log channel
        log_channel_id = await self.bot.db.get_config_id("pt_log_channel")
        channel = self.bot.get_channel(log_channel_id) if log_channel_id is not None else None
        if isinstance(channel, discord.TextChannel):
            await channel.send(f"{interaction.user.mention} (ID: {interaction.user.id}) has applied PT roles to "
                               f"{member.mention} (ID: {member.id})", allowed_mentions=discord.AllowedMentions.none())

    @pt.command(name="switch")
    @is_officer()
    @app_commands.describe(old_role="The role to take away from everyone who has it",
                           new_role="The role to give them instead")
    async def switch(self, interaction: discord.Interaction, old_role: discord.Role, new_role: discord.Role) -> None:
        """ Moves everyone with one role to another, e.g. "PT" to "Former PT" at the end of a semester """

        # Snapshot now so the list can't change between confirming and switching
        members = list(old_role.members)
        if not members:
            await reply(interaction, f"Nobody has the \"{old_role.name}\" role!")
            return

        view = ConfirmView(interaction.user.id)
        await interaction.response.send_message(
            f"This will move **{len(members)}** member(s) from \"{old_role.name}\" to \"{new_role.name}\". Continue?",
            view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(content="Timed out, no roles were changed.", view=None)
            return
        if not view.value:
            return

        await interaction.edit_original_response(content=f"Switching roles for {len(members)} member(s)...")

        failed = []
        for member in members:
            try:
                await member.remove_roles(old_role, reason=f"Role switch by {interaction.user}")
                await member.add_roles(new_role, reason=f"Role switch by {interaction.user}")
            except discord.HTTPException:
                failed.append(member.mention)

        result = f"Moved {len(members) - len(failed)}/{len(members)} member(s) from \"{old_role.name}\" to \"{new_role.name}\"."
        if failed:
            result += f"\nFailed for: {', '.join(failed)}"
        await interaction.edit_original_response(content=result)


async def setup(bot):
    await bot.add_cog(PT(bot))
