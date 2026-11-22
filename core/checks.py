"""
Who can run what. Every staff check reads the role names from here, so renaming a role in the server only
needs a change in this file.
"""
import logging
import typing

import discord
from discord import app_commands

OFFICER_ROLE = "TAO Officer"
PT_ROLE = "PT"
PROF_ROLE = "Prof"

# Roles that count as staff for PT-level commands (private rooms, PT resources)
STAFF_ROLES = (PT_ROLE, PROF_ROLE, OFFICER_ROLE)

# Officer-only command groups are hidden from members without this permission. Server admins can change
# who sees each command in Server Settings -> Integrations without touching the code.
OFFICER_PERMISSIONS = discord.Permissions(manage_roles=True)

Audience = typing.Literal["everyone", "staff", "officer"]


def has_any_role_named(member: discord.abc.User, names: typing.Iterable[str]) -> bool:
    return isinstance(member, discord.Member) and any(role.name in names for role in member.roles)


def audience_of(member: discord.abc.User) -> set[str]:
    """ Which command audiences (see `audience` in command extras) a member belongs to """
    audiences = {"everyone"}
    if has_any_role_named(member, STAFF_ROLES):
        audiences.add("staff")
    if has_any_role_named(member, (OFFICER_ROLE,)):
        audiences.add("officer")
    return audiences


def is_officer():
    """ App command check: only TAO Officers """
    return app_commands.checks.has_any_role(OFFICER_ROLE)


def is_staff():
    """ App command check: PTs, profs and TAO Officers """
    return app_commands.checks.has_any_role(*STAFF_ROLES)


async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    """ Replies to failed slash commands with something readable instead of "The application did not respond" """
    if isinstance(error, (app_commands.MissingAnyRole, app_commands.MissingRole, app_commands.MissingPermissions)):
        message = "You don't have permission to use this command."
    elif isinstance(error, app_commands.NoPrivateMessage):
        message = "This command can only be used in the server."
    elif isinstance(error, app_commands.CheckFailure):
        message = "You can't use this command here."
    else:
        command = interaction.command.qualified_name if interaction.command else "unknown command"
        logging.error(f"Error in /{command}", exc_info=error)
        message = "Something went wrong running this command, please let an officer know!"

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
