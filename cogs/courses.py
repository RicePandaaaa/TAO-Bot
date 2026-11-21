import logging
import typing

import discord
from discord import app_commands
from discord.ext import commands

from checks import OFFICER_PERMISSIONS, is_officer
from DiscordSelect import (COURSES, OFF_CAMPUS, PROF_PROMPT, Course, ProfSelect, class_role_key, menu_order,
                           professor_role_name)
from utils import reply

# Discord's limits for forum channel tags
MAX_FORUM_TAGS = 20
MAX_TAG_NAME_LENGTH = 20


def review_key(course: str) -> str:
    """ Config key for a course's review link, e.g. "review_216" """
    return f"review_{course.split(' ')[1]}"


class Courses(commands.Cog):
    """ /course: everything redone for ENGR 102, PHYS 216 and PHYS 217 each semester """

    course = app_commands.Group(name="course", description="Professor lists, review links and professor menus for each course",
                                default_permissions=OFFICER_PERMISSIONS, guild_only=True, extras={"audience": "officer"})

    def __init__(self, bot):
        self.bot = bot

    @course.command(name="professors")
    @is_officer()
    @app_commands.describe(course="The course to change",
                           names="Every professor's name, separated by commas (Off-Campus is added for you)")
    async def professors(self, interaction: discord.Interaction, course: Course, names: str) -> None:
        """ Replaces a course's professor list (re-post its menu with /course menu afterwards) """

        prof_names = [name.strip() for name in names.split(",") if name.strip() and name.strip() != "TBD"]
        if not prof_names:
            await reply(interaction, "Please provide at least one professor name!")
            return

        # Every course offers Off-Campus (the prompt tells students to pick it), so it is always included
        prof_names = [OFF_CAMPUS if name.lower() == OFF_CAMPUS.lower() else name for name in prof_names]
        if OFF_CAMPUS not in prof_names:
            prof_names.append(OFF_CAMPUS)

        await self.bot.db.set_professors(course, prof_names)
        await reply(interaction, f"The professors for **{course}** are now: {', '.join(menu_order(prof_names))}.\n"
                                 f"Re-post the menu with `/course menu` for the change to show.")

    @course.command(name="list")
    @is_officer()
    @app_commands.describe(course="The course (leave empty for all courses)")
    async def list_courses(self, interaction: discord.Interaction, course: typing.Optional[Course] = None) -> None:
        """ Shows each course's professors and review link """

        lines = []
        for name in ([course] if course else COURSES):
            professors = await self.bot.db.get_professors(name)
            review = await self.bot.db.get_config(review_key(name), "not set")
            lines.append(f"**{name}**\n- Professors: {', '.join(menu_order(professors)) if professors else 'none set'}\n- Review link: {review}")

        await reply(interaction, "\n".join(lines), suppress_embeds=True)

    @course.command(name="review-link")
    @is_officer()
    @app_commands.describe(course="The course the review is for", link="Link to this semester's review resources")
    async def review_link(self, interaction: discord.Interaction, course: Course, link: str) -> None:
        """ Sets a course's review link for this semester (shown in /resources) """

        old_link = await self.bot.db.get_config(review_key(course), "not set")
        await self.bot.db.set_config(review_key(course), link)
        await reply(interaction, f"The {course} review link changed from {old_link} to {link}.", suppress_embeds=True)

    @course.command(name="menu")
    @is_officer()
    @app_commands.describe(course="The course to post the professor menu for",
                           class_role="Role for students in the course",
                           forum="Forum that gets a tag per professor",
                           lab_forum="Optional second forum (e.g. the lab forum) that gets the same tags")
    async def menu(self, interaction: discord.Interaction, course: Course, class_role: discord.Role,
                   forum: discord.ForumChannel, lab_forum: typing.Optional[discord.ForumChannel] = None) -> None:
        """ Posts a course's professor menu here and adds professor tags to its forum(s) """
        assert interaction.guild is not None

        # Every check runs before responding, so mistakes get a private reply and the public
        # response is only ever the menu itself

        # No professors configured for this course
        professors = await self.bot.db.get_professors(course)
        if not professors:
            await reply(interaction, f"There are no professors set for {course}! Use `/course professors` first.")
            return

        # Each professor becomes a forum tag, and Discord caps tag names at 20 characters
        too_long = [prof for prof in professors if len(prof) > MAX_TAG_NAME_LENGTH]
        if too_long:
            await reply(interaction, f"These professor names are longer than {MAX_TAG_NAME_LENGTH} characters and can't be forum tags: "
                                     f"{', '.join(too_long)}. Shorten them (e.g. last name only) with `/course professors`.")
            return

        forums = [forum] if lab_forum is None or lab_forum == forum else [forum, lab_forum]

        # Check every forum's tag limit before changing anything, so a failure leaves the server untouched
        plans = {f: self.plan_forum_tags(f, professors) for f in forums}
        for f, (missing, stale) in plans.items():
            if len(f.available_tags) + len(missing) > MAX_FORUM_TAGS:
                await reply(interaction, f"Adding tags for {', '.join(missing)} would put {f.mention} over Discord's limit of "
                                         f"{MAX_FORUM_TAGS} tags per forum. Delete unused tags in its settings first"
                                         + (f" (these match no current professor: {', '.join(stale)})." if stale else "."))
                return

        # Creating roles and editing forums can take a while: this public "thinking" response becomes the menu
        await interaction.response.defer(thinking=True)

        # Set up the professors' roles and each forum's professor tags
        try:
            await self.setup_professor_roles(course, professors, interaction.guild)
            for f, (missing, _) in plans.items():
                await self.apply_forum_tags(f, missing, course)
        except discord.HTTPException:
            logging.exception(f"Could not set up roles or forum tags for {course}")
            await interaction.delete_original_response()
            await reply(interaction, "Could not create the professor roles or edit the forum tags. "
                                     "Make sure the bot can manage roles and those forum channels.")
            return

        # Remembered so picking a professor for the other PHYS course can find this course's roles
        await self.bot.db.set_config(class_role_key(course), str(class_role.id))

        view = discord.ui.View(timeout=None)
        view.add_item(ProfSelect(course, class_role.id, professors))
        await interaction.followup.send(PROF_PROMPT.format(course=course), view=view)

        # Report the forum changes to the officer only
        lines = []
        for f, (missing, stale) in plans.items():
            line = f"{f.mention}: " + (f"added tags {', '.join(missing)}." if missing else "all professors already had tags.")
            if stale:
                line += f" These tags don't match a current professor: {', '.join(stale)}."
            lines.append(line)
        if any(stale for _, stale in plans.values()):
            lines.append(f"Delete tags you no longer need in the forum's settings (the limit is {MAX_FORUM_TAGS} per forum).")
        await reply(interaction, "\n".join(lines))

    # ---------- Helpers ----------

    @staticmethod
    async def setup_professor_roles(course: str, professors: list[str], guild: discord.Guild) -> None:
        """ Creates any missing professor roles (e.g. "216 Brooks") """
        for professor in professors:
            role_name = professor_role_name(course, professor)
            if not discord.utils.get(guild.roles, name=role_name):
                await guild.create_role(name=role_name, reason=f"Professor role for {course}")

    @staticmethod
    def plan_forum_tags(forum: discord.ForumChannel, professors: list[str]) -> tuple[list[str], list[str]]:
        """
        Compares a forum's tags with the professor list (case-insensitive) without changing anything

        :return: Professors that still need a tag, and existing tags that match no current professor
        """
        existing_names = {tag.name.lower() for tag in forum.available_tags}
        professor_names = {prof.lower() for prof in professors}

        missing = [prof for prof in professors if prof.lower() not in existing_names]
        stale = [tag.name for tag in forum.available_tags if tag.name.lower() not in professor_names]
        return missing, stale

    @staticmethod
    async def apply_forum_tags(forum: discord.ForumChannel, missing: list[str], course: str) -> None:
        """
        Adds the missing professor tags. Existing tags are never removed, so manually added tags
        (e.g. "Solved") and tags on old posts are kept.
        """
        if missing:
            await forum.edit(available_tags=list(forum.available_tags) + [discord.ForumTag(name=prof) for prof in missing],
                             require_tag=False,
                             reason=f"Professor tags for {course}")


async def setup(bot):
    await bot.add_cog(Courses(bot))
