import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from checks import STAFF_ROLES, has_any_role_named
from utils import link_embed


class Resources(commands.Cog):
    """ /resources: every link collection the bot can post, one topic at a time """

    def __init__(self, bot):
        self.bot = bot

    async def freshman(self) -> discord.Embed:
        return link_embed("Help Centers", {
            "ETAM Information": "https://engineering.tamu.edu/academics/undergraduate/entry-to-a-major/index.html",
            "University Writing Center": "https://writingcenter.tamu.edu/",
            "Academic Success Center": "https://engineering.tamu.edu/academics/academic-support-services.html",
            "Texas A&M Main Calendar": "https://calendar.tamu.edu/",
            "Student Interest Events": "https://calendar.tamu.edu/student-interest/all",
            "University Art Galleries": "https://uart.tamu.edu/",
        })

    async def mental_health(self) -> discord.Embed:
        return link_embed("Mental Health Resources", {
            "University Health Services": "https://mentalhealth.tamu.edu/students/index.html",
            "TELUS Health Student Support App (24/7)": "https://uhs.tamu.edu/mental-health/student-support.html",
            "Texas A&M University Helplines": "https://mentalhealth.tamu.edu/crisis-resources.html",
            "National Suicide and Crisis Lifeline (24/7)": "[Call 988](tel:988)",
            "Crisis Text Hotline": "[Text HOME to 741741](sms:741741?body=HOME)",
        })

    async def career_fair(self) -> discord.Embed:
        return link_embed("Career Fair Resources", {
            "Career Fair List": "https://careercenter.tamu.edu/events-and-programs/career-fairs/",
            "SEC Career Fair": "https://www.careerfair.sec.tamu.edu/",
            "Career Fair Preparation": "https://careercenter.tamu.edu/current-students/find-an-internship-job/career-fair-preparation/",
            "Professional Attire Guides": "https://careercenter.tamu.edu/current-students/interviews-and-offers/dress-for-success/",
            "Career Closet": "https://careercloset.tamu.edu/",
            "Free Professional Headshots": "https://careercenter.tamu.edu/about/services/#professional-photo-pod",
        }, description="Career fairs are in-person or virtual events where students connect with employer representatives to "
                       "explore internships, entry-level jobs, and build professional networks. For more information on preparing "
                       "for and attending career fairs, visit the [Career Center](https://careercenter.tamu.edu/about/).")

    async def tao(self) -> discord.Embed:
        db = self.bot.db
        return link_embed("Resources made by TAO!", {
            # Discord rejects empty field values, so this heading-only field uses a zero-width space
            "Reviews and Resources from previous and current semesters can be found in the TAO Drive!": "​",
            "TAO Drive": "https://tx.ag/taoreviewdrive",
            "216/217 Lab Helpful Info": "https://docs.google.com/presentation/d/10ZxiElBy0SsB5s-FwOXpJD-jiORtwtdnGqKG4CxraZE/edit#slide=id.p",
            "102 Helpful Info": "In progress!",
            "216 Review (Current Semester)": await db.get_config("review_216", "N/A"),
            "217 Review (Current Semester)": await db.get_config("review_217", "N/A"),
            "102 Review (Current Semester)": await db.get_config("review_102", "N/A"),
        })

    async def links(self) -> discord.Embed:
        return link_embed("ENGR TAO Links", {
            "bento.me": "https://bento.me/engrtao",
            "Discord": "https://tx.ag/taoserver",
            "YouTube": "https://www.youtube.com/@engrtao",
            "Instagram": "https://instagram.com/tamutao",
            "LinkedIn": "https://www.linkedin.com/company/engr-tao/",
        }, color=discord.Color.random())

    async def pt(self) -> discord.Embed:
        return link_embed("Helpful Resources for PTs!", {
            "Info for New PTs (Google Doc)": "https://docs.google.com/document/d/1JvCgARe7d32JmA3MvYfoq2PwR3YdfZpuK48feHKUvtk/edit#heading=h.gwwqgp1crfcc",
            "How to Log Hours (Discord Message Chain)": "https://discord.com/channels/1022962971607060540/1143205554362269788/1143936580243968090",
            "216/217 Lab - Helpful Info (Google Slides)": "https://docs.google.com/presentation/d/10ZxiElBy0SsB5s-FwOXpJD-jiORtwtdnGqKG4CxraZE/edit#slide=id.p",
        })

    @app_commands.command(name="resources", extras={"audience": "everyone"})
    @app_commands.describe(topic="Which resources to show")
    @app_commands.choices(topic=[
        Choice(name="Freshman information", value="freshman"),
        Choice(name="Mental health", value="mental_health"),
        Choice(name="Career fairs", value="career_fair"),
        Choice(name="TAO reviews and materials", value="tao"),
        Choice(name="TAO links and socials", value="links"),
        Choice(name="PT resources (PTs and staff only)", value="pt"),
    ])
    async def resources(self, interaction: discord.Interaction, topic: Choice[str]) -> None:
        """ Posts helpful links: freshman info, mental health, career fairs, TAO reviews, and more """

        if topic.value == "pt" and not has_any_role_named(interaction.user, STAFF_ROLES):
            await interaction.response.send_message("PT resources are only available to PTs, profs and officers.", ephemeral=True)
            return

        embed = await getattr(self, topic.value)()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Resources(bot))
