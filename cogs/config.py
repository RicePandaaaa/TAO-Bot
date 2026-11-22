import typing

import discord
from discord import app_commands
from discord.ext import commands

from core.checks import OFFICER_PERMISSIONS, is_officer
from core.db import CONFIG_KEYS
from core.utils import reply

ConfigKey = typing.Literal[
    "welcome_role_1",
    "welcome_role_2",
    "pt_log_channel",
    "private_category",
    "archive_category",
    "room_close_role",
    "review_216",
    "review_217",
    "review_102",
]


def is_role_key(key: str) -> bool:
    """ Whether a config key holds a role ID """
    return key.startswith("welcome_role") or key.endswith("_role")


class Config(commands.Cog):
    """ /config: the bot's settings, changed live without a restart """

    config = app_commands.Group(name="config", description="View and change the bot's settings",
                                default_permissions=OFFICER_PERMISSIONS, guild_only=True, extras={"audience": "officer"})

    def __init__(self, bot):
        self.bot = bot

    @config.command(name="set")
    @is_officer()
    @app_commands.describe(key="The setting to change", value="The new value (an ID for role/channel/category settings)")
    async def set_value(self, interaction: discord.Interaction, key: ConfigKey, value: str) -> None:
        """ Changes a setting, taking effect immediately """
        assert interaction.guild is not None
        guild = interaction.guild

        # Validate that ID-typed keys point to a real role/channel/category in this server
        if is_role_key(key):
            if not value.isdigit() or guild.get_role(int(value)) is None:
                await reply(interaction, f"\"{value}\" is not the ID of a role in this server!")
                return

        elif key.endswith("_channel"):
            if not value.isdigit() or not isinstance(guild.get_channel(int(value)), discord.TextChannel):
                await reply(interaction, f"\"{value}\" is not the ID of a text channel in this server!")
                return

        elif key.endswith("_category"):
            if not value.isdigit() or not isinstance(guild.get_channel(int(value)), discord.CategoryChannel):
                await reply(interaction, f"\"{value}\" is not the ID of a category in this server!")
                return

        old_value = await self.bot.db.get_config(key, "N/A")
        await self.bot.db.set_config(key, value)
        await reply(interaction, f"\"{key}\" changed from \"{old_value}\" to \"{value}\".")

    @config.command(name="get")
    @is_officer()
    @app_commands.describe(key="The setting to look up")
    async def get_value(self, interaction: discord.Interaction, key: ConfigKey) -> None:
        """ Shows the current value of one setting """

        value = await self.bot.db.get_config(key)
        await reply(interaction, f"\"{key}\" is currently set to \"{value if value is not None else 'N/A'}\".")

    @config.command(name="list")
    @is_officer()
    async def list_values(self, interaction: discord.Interaction) -> None:
        """ Shows every setting and its current value """

        config = await self.bot.db.all_config()

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Bot Configuration")

        for key in CONFIG_KEYS:
            value = config.get(key, "N/A")
            embed.add_field(name=key, value=self.format_value(interaction.guild, key, value), inline=False)

        await reply(interaction, embed=embed)

    @config.command(name="verification")
    @is_officer()
    @app_commands.describe(name="Name of the officer PTs and faculty should contact",
                           user="That officer's Discord account",
                           email="Their official TAMU email (ends in @tamu.edu)")
    async def verification(self, interaction: discord.Interaction, name: str, user: discord.Member, email: str) -> None:
        """ Changes who PTs and faculty contact to get verified """

        if not email.lower().endswith("@tamu.edu"):
            await reply(interaction, "You must specify an official TAMU email.")
            return

        await self.bot.db.set_config("verify_name", name)
        await self.bot.db.set_config("verify_user_id", str(user.id))
        await self.bot.db.set_config("verify_email", email)

        await reply(interaction, f"PT/faculty verification contact changed to {name} ({user.mention}), email: {email}. "
                                 f"Re-post the verification prompt with `/post verification` for the change to show.")

    @staticmethod
    def format_value(guild: discord.Guild | None, key: str, value: str) -> str:
        """ Resolves ID values to mentions where possible so the list is readable """
        if guild is None or not value.isdigit():
            return value

        if is_role_key(key):
            role = guild.get_role(int(value))
            return f"{role.mention} ({value})" if role is not None else f"{value} (role not found!)"

        if key.endswith("_channel") or key.endswith("_category"):
            channel = guild.get_channel(int(value))
            return f"{channel.mention} ({value})" if channel is not None else f"{value} (channel not found!)"

        return value


async def setup(bot):
    await bot.add_cog(Config(bot))
