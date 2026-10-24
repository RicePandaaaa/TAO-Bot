"""Dropdown and back-button navigation for the help menu."""

import discord
import help_content


class HelpView(discord.ui.View):
    @discord.ui.select(
        placeholder="Choose a topic...",
        options=[
            discord.SelectOption(
                label="/howdy",
                value="howdy",
                description="Learn more about the bot and what it does.",
            ),
            discord.SelectOption(
                label="/taoresources",
                value="taoresources",
                description="Find TAO study and review materials.",
            ),
            discord.SelectOption(
                label="/mental_health_resources",
                value="mental_health_resources",
                description="Resources for mental health",
            ),
            discord.SelectOption(
                label="/freshman_information",
                value="freshman_information",
                description="Information and resources for freshman",
            ),
            discord.SelectOption(
                label="/links",
                value="links",
                description="Relevant social media links for TAO",
            ),
            discord.SelectOption(
                label="/close",
                value="close",
                description="Closes a private channel (student only)",
            ),
            discord.SelectOption(
                label="/code",
                value="code",
                description="Guidelines for sharing assignment code.",
            ),
        ]
    )
    async def select_command(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ):
        # Acknowledge the selection before reading resource links from the database.
        await interaction.response.defer()
        command = select.values[0]

        if command == "howdy":
            card = help_content.howdy_card(interaction.user.id)
        elif command == "code":
            card = help_content.code_card(interaction.user.id)
        elif command == "taoresources":
            card = await help_content.taoresources_card(interaction.client.db)
        else:
            builders = {
                "freshman_information": help_content.freshman_information_card,
                "mental_health_resources": help_content.mental_health_resources_card,
                "links": help_content.links_card,
                "close": help_content.close_card,
            }
            card = builders[command]()

        await interaction.edit_original_response(
            embed=card,
            view=HelpDetailView(),
        )


class HelpDetailView(discord.ui.View):
    @discord.ui.button(
        label="← All Commands",
        style=discord.ButtonStyle.secondary,
    )
    async def back_to_overview(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            embed=help_content.help_overview(),
            view=HelpView(),
        )
