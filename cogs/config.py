import typing

import discord
from discord.ext import commands
from discord.ext.commands import Context

from db import CONFIG_KEYS

ConfigKey = typing.Literal[
    "welcome_role_1",
    "welcome_role_2",
    "pt_log_channel",
    "private_category",
    "archive_category",
    "review_216",
    "review_217",
    "review_102",
]


class Config(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def config_set(self, ctx: Context,
                         key: ConfigKey = commands.parameter(description="The config key to change"),
                         value: str = commands.parameter(description="The new value (an ID for role/channel/category keys)")):
        """ Sets a config value, taking effect immediately without a restart """

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        # Validate that ID-typed keys point to a real role/channel/category in this server
        if key.startswith("welcome_role"):
            if not value.isdigit() or ctx.guild.get_role(int(value)) is None:
                await ctx.send(f"\"{value}\" is not the ID of a role in this server!")
                return

        elif key.endswith("_channel"):
            if not value.isdigit() or not isinstance(ctx.guild.get_channel(int(value)), discord.TextChannel):
                await ctx.send(f"\"{value}\" is not the ID of a text channel in this server!")
                return

        elif key.endswith("_category"):
            if not value.isdigit() or not isinstance(ctx.guild.get_channel(int(value)), discord.CategoryChannel):
                await ctx.send(f"\"{value}\" is not the ID of a category in this server!")
                return

        old_value = await self.bot.db.get_config(key, "N/A")
        await self.bot.db.set_config(key, value)
        await ctx.send(f"Config \"{key}\" has been changed from \"{old_value}\" to \"{value}\"!")

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def config_get(self, ctx: Context,
                         key: ConfigKey = commands.parameter(description="The config key to look up")):
        """ Shows the current value of a config key """

        value = await self.bot.db.get_config(key)
        await ctx.send(f"Config \"{key}\" is currently set to \"{value if value is not None else 'N/A'}\".")

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def config_list(self, ctx: Context):
        """ Shows all config keys and their current values """

        config = await self.bot.db.all_config()

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="Bot Configuration")

        for key in CONFIG_KEYS:
            value = config.get(key, "N/A")
            embed.add_field(name=key, value=self.format_value(ctx, key, value), inline=False)

        await ctx.send(embed=embed)

    def format_value(self, ctx: Context, key: str, value: str) -> str:
        """ Resolves ID values to mentions where possible so the list is readable """
        if ctx.guild is None or not value.isdigit():
            return value

        if key.startswith("welcome_role"):
            role = ctx.guild.get_role(int(value))
            return f"{role.mention} ({value})" if role is not None else f"{value} (role not found!)"

        if key.endswith("_channel") or key.endswith("_category"):
            channel = ctx.guild.get_channel(int(value))
            return f"{channel.mention} ({value})" if channel is not None else f"{value} (channel not found!)"

        return value


async def setup(bot):
    await bot.add_cog(Config(bot))
