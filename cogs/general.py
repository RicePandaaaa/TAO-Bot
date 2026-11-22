import typing

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context, Greedy

from core.checks import OFFICER_ROLE, audience_of

# Sections of /help, in order, keyed by the `audience` set in each command's extras
HELP_SECTIONS = {
    "everyone": "Commands for everyone",
    "staff": "For PTs, profs and officers",
    "officer": "For officers",
}


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Prefix-only on purpose: a slash version would be visible to everyone and can't be used to fix a broken sync
    @commands.command()
    @commands.guild_only()
    @commands.has_any_role(OFFICER_ROLE)
    async def sync(self, ctx: Context,
                   guilds: Greedy[discord.Object] = commands.parameter(default=None, description="A list of guilds to go through"),
                   spec: typing.Optional[typing.Literal["~", "*", "^"]] = commands.parameter(default=None, description="Type of sync to be performed")) -> None:
        """
        Syncs the slash commands with Discord (run this after adding, removing or renaming commands)
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current server'}.")
            return

        # Sync to each guild that was given, skipping any the bot can't sync to
        synced_count = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                synced_count += 1

        await ctx.send(f"Synced the tree to {synced_count}/{len(guilds)} servers.")

    @app_commands.command(name="help", extras={"audience": "everyone"})
    async def help(self, interaction: discord.Interaction) -> None:
        """ What this bot does and the commands you can use """

        audiences = audience_of(interaction.user)
        sections: dict[str, list[str]] = {audience: [] for audience in HELP_SECTIONS}

        # Built from the registered commands, so it never goes out of date
        for command in sorted(self.bot.tree.get_commands(), key=lambda c: c.name):
            group_audience = command.extras.get("audience", "everyone")
            subcommands = command.commands if isinstance(command, app_commands.Group) else [command]

            for sub in subcommands:
                audience = sub.extras.get("audience", group_audience)
                if audience in audiences:
                    sections[audience].append(f"`/{sub.qualified_name}`: {sub.description}")

        description = ("Howdy! I'm the ENGR TAO server's bot. I handle role selection, private rooms for one-on-one "
                       "help with PTs, and links to resources for freshmen, PTs, and TAO reviews.")
        for audience, title in HELP_SECTIONS.items():
            if sections[audience]:
                description += f"\n\n**{title}**\n" + "\n".join(sections[audience])

        embed = discord.Embed(color=discord.Color.dark_red(), description=description)
        embed.set_author(name="TAO Bot Help")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="code", extras={"audience": "everyone"})
    async def code(self, interaction: discord.Interaction) -> None:
        """ Reminds everyone never to share code from their assignments """

        await interaction.response.send_message(
            f"Howdy, {interaction.user.mention} would like to remind you to **NEVER SHARE ANY PART OF YOUR CODE THAT IS USED IN YOUR SUBMITTED ASSIGNMENTS.**"
            " You can only share code that was created for purposes unrelated to your assignments."
            " Posting your code used in assignments (such as labs and HW) can and will lead to severe consequences.")


async def setup(bot):
    await bot.add_cog(General(bot))
