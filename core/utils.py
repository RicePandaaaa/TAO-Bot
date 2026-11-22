import discord


async def reply(interaction: discord.Interaction, content: str | None = None, *, ephemeral: bool = True, **kwargs) -> None:
    """ Responds to an interaction, or sends a follow-up if it was already responded to (e.g. deferred) """
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral, **kwargs)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)


def link_embed(title: str, fields: dict[str, str], description: str | None = None,
               color: discord.Color | None = None) -> discord.Embed:
    """ Builds the bot's standard embed: a title and one non-inline field per entry """
    embed = discord.Embed(color=color or discord.Color.dark_red(), description=description)
    embed.set_author(name=title)
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed
