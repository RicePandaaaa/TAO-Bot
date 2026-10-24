"""Shared resource cards used by standalone commands and the help menu."""

import discord
from db import Database


def help_overview() -> discord.Embed:
    card = discord.Embed(
        title="TAO Bot Help",
        description=(
            "Choose a topic to find resources and bot guidance.\n"
            "\u200b"
        ),
        color=discord.Color.dark_red()
    )
    
    card.add_field(
        name="👋 About the Bot",
        value="`/howdy` - Learn more about the bot and what it does.",
        inline=False
    )

    card.add_field(
        name="📚 Study Resources",
        value="`/taoresources` - Find TAO study and review materials.",
        inline=False
    )

    card.add_field(
        name="💚 Mental Health Resources",
        value="`/mental_health_resources` - Resources for mental health",
        inline=False
    )

    card.add_field(
        name="💡 Freshman Information",
        value="`/freshman_information` - Information and resources for freshman",
        inline=False
    )

    card.add_field(
        name="💻 Sharing Code Policy",
        value=(
            "`/code` - Guidelines for sharing assignment code.\n"
            "\u200b"
        ),
        inline=False,
    )

    card.add_field(
        name="🌐 Links",
        value="`/links` - Relevant social media links for TAO",
        inline=False
    )

    card.add_field(
        name="🔒 Close",
        value="`/close` - Closes a private channel (student only)",
        inline=False
    )

    card.set_footer(text="Select a command below to learn more.")
    return card


def howdy_card(user_id: int) -> discord.Embed:
    return discord.Embed(
        title="About TAO Bot",
        description=(
            f"Howdy <@{user_id}>, I was created to assist PTs and professors in managing "
            "voice channels for one-on-one sessions for students and content reviews. "
            "I can also provide students with information related to office hours! "
            "Please type `tao.help` for a complete command list!"
        ),
        color=discord.Color.dark_red(),
    )


def freshman_information_card() -> discord.Embed:
    fields = {
        "ETAM Information": "https://engineering.tamu.edu/academics/undergraduate/entry-to-a-major/index.html",
        "University Writing Center": "https://writingcenter.tamu.edu/",
        "Academic Success Center": "https://engineering.tamu.edu/academics/academic-support-services.html",
        "Texas A&M Main Calendar": "https://calendar.tamu.edu/",
        "Student Interest Events": "https://calendar.tamu.edu/student-interest/all",
        "University Art Galleries": "https://uart.tamu.edu/"
    }

    # Make the embed
    embed = discord.Embed(color=discord.Color.dark_red())
    embed.set_author(name="Help Centers")

    # Add the fields
    for field_name in fields:
        embed.add_field(name=field_name, value=fields[field_name], inline=False)

    return embed


def mental_health_resources_card() -> discord.Embed:
    fields = {
        "University Health Services": "https://mentalhealth.tamu.edu/students/index.html",
        "TELUS Health Student Support App (24/7)": "https://uhs.tamu.edu/mental-health/student-support.html",
        "Texas A&M University Helplines": "https://mentalhealth.tamu.edu/crisis-resources.html",
        "National Suicide and Crisis Lifeline (24/7)": "[Call 988](tel:988)",
        "Crisis Text Hotline": "[Text HOME to 741741](sms:741741?body=HOME)"
    }

    embed = discord.Embed(color=discord.Color.dark_red())
    embed.set_author(name="Mental Health Resources")

    for field_name in fields:
        embed.add_field(name=field_name, value=fields[field_name], inline=False)
    return embed


def links_card() -> discord.Embed:
    embed = discord.Embed(color=discord.Color.dark_red())
    embed.set_author(name="ENGR TAO Links")

    # Add values to embed
    links = {"bento.me":   "https://bento.me/engrtao",
             "Discord":    "https://tx.ag/taoserver",
             "YouTube":    "https://www.youtube.com/@engrtao",
             "Instagram":  "https://instagram.com/tamutao",
             "LinkedIn":   "https://www.linkedin.com/company/engr-tao/"}   

    for key in links.keys():
        embed.add_field(name=key, value=links[key], inline=False)

    return embed


async def taoresources_card(db: Database) -> discord.Embed:
    fields = {
        "TAO Drive": "https://tx.ag/taoreviewdrive",
        "216/217 Lab Helpful Info": "https://docs.google.com/presentation/d/10ZxiElBy0SsB5s-FwOXpJD-jiORtwtdnGqKG4CxraZE/edit#slide=id.p",
        "102 Helpful Info": "In progress!",
        "216 Review (Current Semester)": await db.get_config("review_216", "N/A"),
        "217 Review (Current Semester)": await db.get_config("review_217", "N/A"),
        "102 Review (Current Semester)": await db.get_config("review_102", "N/A")
    }

    # Make the embed
    embed = discord.Embed(
        color=discord.Color.dark_red(),
        description="Reviews and resources from previous and current semesters can be found in the TAO Drive!",
    )
    embed.set_author(name="Resources made by TAO!")

    # Add the fields
    for field_name in fields:
        embed.add_field(name=field_name, value=fields[field_name], inline=False)

    return embed


def close_card() -> discord.Embed:
    return discord.Embed(
        title="Closing a Private Room",
        description=(
            "Run `/close` inside your private help room when you are finished.\n\n"
            "Only the student the room was created for can close it. "
            "The command locks the room and moves it to the archive.\n\n"
            "Opening this help page does not close your room."
        ),
        color=discord.Color.dark_red(),
    )


def code_card(user_id: int) -> discord.Embed:
    return discord.Embed(
        title="Sharing Assignment Code",
        description=(
            f"Howdy, <@{user_id}>. We would like to remind you to "
            "**NEVER SHARE ANY PART OF YOUR CODE THAT IS USED IN YOUR SUBMITTED ASSIGNMENTS.**"
            " You can only share code that was created for purposes unrelated to your assignments."
            " Posting your code used in assignments (such as labs and HW) can and will lead to severe consequences."
        ),
        color=discord.Color.dark_red(),
    )
