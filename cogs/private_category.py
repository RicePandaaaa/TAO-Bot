import discord
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from discord.ext import commands
from discord.ext.commands import Context


class PrivateCategory(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.private_category_id = 1488619460897280222
        self.archive_category_id = 0
        
        self.channel_students: dict[int, int] = {}

    @commands.hybrid_command()
    @commands.has_any_role("PT")
    async def room(self, ctx: Context,
                   user: discord.Member = commands.parameter(description="The user to create a private room for")) -> None:
        """ Creates a private channel in the designated category for the given user """

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        category = ctx.guild.get_channel(self.private_category_id)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await ctx.send("Could not find the private category", ephemeral=True)
            return

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        now = datetime.now(ZoneInfo("America/Chicago"))
        date_str = now.strftime("%b%d%y-%H%M").lower()  # e.g. mar3126-1453
        channel_name = f"{user.display_name.lower().replace(' ', '-')}-{date_str}"
        channel = await category.create_text_channel(name=channel_name, overwrites=overwrites)
        self.channel_students[channel.id] = user.id

        await ctx.send(f"Created private room {channel.mention} for {user.mention}.", ephemeral=True)


    @commands.hybrid_command()
    async def close(self, ctx: Context) -> None:
        """ Closes this private channel (student only): locks it and moves it to the archive """

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send("This command can only be used in a text channel.", ephemeral=True)
            return

        channel = ctx.channel
        student_id = self.channel_students.get(channel.id)

        if student_id is None:
            await ctx.send("This command can only be used in a private room.", ephemeral=True)
            return

        if ctx.author.id != student_id:
            await ctx.send("Only the student this room was created for can close it.", ephemeral=True)
            return

        archive_category = ctx.guild.get_channel(self.archive_category_id)
        if archive_category is None or not isinstance(archive_category, discord.CategoryChannel):
            await ctx.send("Could not find the archive category.", ephemeral=True)
            return

        # Lock the channel for everyone, then move to archive
        overwrites = channel.overwrites
        for target in overwrites:
            overwrites[target].send_messages = False
        overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(view_channel=False, send_messages=False)

        await channel.edit(overwrites=overwrites, category=archive_category)
        del self.channel_students[channel.id]

        await ctx.send("This room has been closed and archived.", ephemeral=True)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def archive_rooms(self, ctx: Context) -> None:
        """ Moves private channels inactive for 7+ days into the archive category """

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        private_category = ctx.guild.get_channel(self.private_category_id)
        if private_category is None or not isinstance(private_category, discord.CategoryChannel):
            await ctx.send("Could not find the private category", ephemeral=True)
            return

        archive_category = ctx.guild.get_channel(self.archive_category_id)
        if archive_category is None or not isinstance(archive_category, discord.CategoryChannel):
            await ctx.send("Could not find the archive category", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        archived = []

        for channel in private_category.text_channels:
            last_message = channel.last_message_id

            # No messages ever sent — use channel creation time
            if last_message is None:
                last_activity = channel.created_at
            else:
                last_activity = discord.utils.snowflake_time(last_message)

            if (now - last_activity).days >= 7:
                await channel.edit(category=archive_category)
                archived.append(channel.mention)

        if archived:
            await ctx.send(f"Archived {len(archived)} channel(s): {', '.join(archived)}.", ephemeral=True)
        else:
            await ctx.send("No channels were inactive long enough to archive.", ephemeral=True)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_private_category(self, ctx: Context,
                    category_id: str = commands.parameter(description="The ID of the private category")) -> None:
        """ Sets the private category for the server """

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        self.private_category_id = int(category_id)

        await ctx.send(f"Private category set to {category_id}.", ephemeral=True)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def set_archive_category(self, ctx: Context,
                                         category_id: str = commands.parameter(description="The ID of the archive category")) -> None:
        """ Sets the archive category for the server """

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        self.archive_category_id = int(category_id)

        await ctx.send(f"Archive category set to {category_id}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PrivateCategory(bot))
