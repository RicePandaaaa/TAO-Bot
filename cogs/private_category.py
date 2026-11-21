import discord
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from discord import app_commands
from discord.ext import commands

from checks import is_officer, is_staff
from utils import reply

# Rooms with no messages for this many days are archived by /room archive
INACTIVE_DAYS = 7


class PrivateCategory(commands.Cog):
    """ Private rooms for one-on-one help between a PT and a student """

    room = app_commands.Group(name="room", description="Private rooms for one-on-one help with a PT",
                              guild_only=True, extras={"audience": "staff"})

    def __init__(self, bot):
        self.bot = bot

    async def get_category(self, guild: discord.Guild, key: str) -> discord.CategoryChannel | None:
        """ Looks up a category from config ("private_category" or "archive_category") """

        # Check for category within the database
        category_id = await self.bot.db.get_config_id(key)
        if category_id is None:
            return None

        # Ensure retrieved ID is actually of a category
        category = guild.get_channel(category_id)
        return category if isinstance(category, discord.CategoryChannel) else None

    async def archive_channel(self, channel: discord.TextChannel, archive_category: discord.CategoryChannel) -> None:
        """ Locks a private room for everyone, moves it to the archive, and forgets it in the database """
        overwrites = channel.overwrites
        for target in overwrites:
            overwrites[target].send_messages = False
        overwrites[channel.guild.default_role] = discord.PermissionOverwrite(view_channel=False, send_messages=False)

        await channel.edit(overwrites=overwrites, category=archive_category)
        await self.bot.db.remove_room(channel.id)

    @room.command(name="create")
    @is_staff()
    @app_commands.describe(user="The student to create a private room for")
    async def create(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """ Creates a private channel for you and a student """
        assert interaction.guild is not None

        # Allows the interaction response window to be extended due to length of execution of command
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Ensure the private channel category exists
        category = await self.get_category(interaction.guild, "private_category")
        if category is None:
            await reply(interaction, "Could not find the private category. Set it with `/config set private_category <ID>`.")
            return

        # Absorb category permissions before ensuring regular users cannot see this room
        overwrites = category.overwrites
        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        overwrites[user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Format channel name based on date and time
        now = datetime.now(ZoneInfo("America/Chicago"))
        date_str = now.strftime("%b%d%y-%H%M").lower()  # e.g. mar3126-1453
        channel_name = f"{user.display_name.lower().replace(' ', '-')}-{date_str}"
        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        await self.bot.db.add_room(channel.id, user.id)

        await reply(interaction, f"Created private room {channel.mention} for {user.mention}.")

    @room.command(name="archive", extras={"audience": "officer"})
    @is_officer()
    async def archive(self, interaction: discord.Interaction) -> None:
        """ Locks and archives every private room with no messages in the last 7 days """
        assert interaction.guild is not None

        await interaction.response.defer(ephemeral=True, thinking=True)

        private_category = await self.get_category(interaction.guild, "private_category")
        if private_category is None:
            await reply(interaction, "Could not find the private category.")
            return

        archive_category = await self.get_category(interaction.guild, "archive_category")
        if archive_category is None:
            await reply(interaction, "Could not find the archive category. Set it with `/config set archive_category <ID>`.")
            return

        now = datetime.now(timezone.utc)
        archived = []

        for channel in private_category.text_channels:
            last_message = channel.last_message_id

            # Use channel creation time if no messages exist
            if last_message is None:
                last_activity = channel.created_at
            else:
                last_activity = discord.utils.snowflake_time(last_message)

            if (now - last_activity).days >= INACTIVE_DAYS:
                await self.archive_channel(channel, archive_category)
                archived.append(channel.mention)

        if archived:
            await reply(interaction, f"Archived {len(archived)} channel(s): {', '.join(archived)}.")
        else:
            await reply(interaction, "No channels were inactive long enough to archive.")

    @app_commands.command(name="close", extras={"audience": "everyone"})
    @app_commands.guild_only()
    async def close(self, interaction: discord.Interaction) -> None:
        """ Closes the private room you're in: locks it and moves it to the archive """
        assert interaction.guild is not None

        # Allows the interaction response window to be extended due to length of execution of command
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not isinstance(interaction.channel, discord.TextChannel):
            await reply(interaction, "This command can only be used in a text channel.")
            return

        # Ensure the channel in which the command is invoked is valid
        channel = interaction.channel
        student_id = await self.bot.db.get_room_student(channel.id)

        if student_id is None:
            await reply(interaction, "This command can only be used in a private room.")
            return

        # Besides the student, members with the configured staff role may close the room
        close_role_id = await self.bot.db.get_config_id("room_close_role")
        has_close_role = (close_role_id is not None and isinstance(interaction.user, discord.Member)
                          and interaction.user.get_role(close_role_id) is not None)

        if interaction.user.id != student_id and not has_close_role:
            await reply(interaction, "Only the student this room was created for (or staff) can close it.")
            return

        archive_category = await self.get_category(interaction.guild, "archive_category")
        if archive_category is None:
            await reply(interaction, "Could not find the archive category.")
            return

        await self.archive_channel(channel, archive_category)

        await reply(interaction, "This room has been closed and archived.")


async def setup(bot):
    await bot.add_cog(PrivateCategory(bot))
