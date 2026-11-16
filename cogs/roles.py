import logging

import discord
from discord.ext import commands
from discord.ext.commands import Context

from DiscordSelect import (PRONOUN_ROLES_KEY, ProfSelect, PronounsSelect, StudentSelect,
                           announcements_view, review_view)
from views.confirm import ConfirmView

MAX_NICKNAME_LENGTH = 32

# Discord's limits for forum channel tags
MAX_FORUM_TAGS = 20
MAX_TAG_NAME_LENGTH = 20

class Roles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(description="Basic command to show buttons for opting in and out of two different announcements roles")
    @commands.has_any_role("TAO Officer")
    async def send_announcements_prompt(self, ctx: Context,
                                        server_role: discord.Role = commands.parameter(description="Server/TAO announcements role"),
                                        board_role:  discord.Role = commands.parameter(description="Bulletin Board announcements role")) -> None:
        
        """ Basic command to show buttons for opting in and out of two different announcements roles """

        message = f"For announcement pings, you may have the following roles:\n" \
                  f"- \"{server_role.name}\" : For server/TAO club announcements\n" \
                  f"- \"{board_role.name}\" : For announcements posted in the bulletin board channel\n\n" \
                  f"The button options below allow you to opt in or opt out these roles as stated:\n" \
                  f"- 1) Opt **into** \"{server_role.name}\"\n" \
                  f"- 2) Opt **into** \"{board_role.name}\"\n" \
                  f"- 3) Opt **out of** \"{server_role.name}\"\n" \
                  f"- 4) Opt **out of** \"{board_role.name}\""
        await ctx.send(message, view=announcements_view(server_role, board_role))


    @commands.hybrid_command(description="Basic command to show buttons for opting in and out of TAO review roles")
    @commands.has_any_role("TAO Officer")
    async def send_tao_review_prompt(self, ctx: Context,
                                        review_role: discord.Role = commands.parameter(description="TAO review role")) -> None:
        
        """ Basic command to show buttons for opting in and out of TAO review roles """

        message = f"For pings regarding TAO reviews, there is \"{review_role.name}\"!\n" \
                  f"The button options below allow you to opt in or opt out this role as stated:\n" \
                  f"- 1) Opt **into** \"{review_role.name}\"\n" \
                  f"- 2) Opt **out of** \"{review_role.name}\"\n"
        await ctx.send(message, view=review_view(review_role))


    @commands.hybrid_command(description="Basic command to send welcome prompt and assign roles")
    @commands.has_any_role("TAO Officer")
    async def send_welcome_prompt(self, ctx: Context, 
                                  doing_etam_role:       discord.Role = commands.parameter(description="Role to assign to those still in the ETAM process"),
                                  done_with_etam_role:   discord.Role = commands.parameter(description="Role to assign to those who have completed the ETAM process"),
                                  visiting_student_role: discord.Role = commands.parameter(description="Role to assign to those just visiting the server"),
                                  alumni_role:           discord.Role = commands.parameter(description="Role to assign to alumni"),
                                  ) -> None:
        
        """ Basic command to send welcome prompt and assign roles """

        view = discord.ui.View(timeout=None)
        student_select_menu = StudentSelect([doing_etam_role.id, done_with_etam_role.id,
                                             visiting_student_role.id, alumni_role.id])
        view.add_item(student_select_menu)

        await ctx.send("Welcome to the TAO server! If you have not already, please **read the newcomer tips at " \
                       "<#1144274416965013565> and the server guidelines at <#1023087608928153681>**. Also, please select what type of student you are (you can change this later)." \
                       "Do note that **your selection can only be changed by a mod**, so please be very careful which option you choose!", view=view)


    @commands.hybrid_command(description="Basic command to send prompt for professor and class role assignments")
    @commands.has_any_role("TAO Officer")
    async def send_prof_prompt(self, ctx: Context,
                               prompt: str = commands.parameter(description="The prompt text"),
                               class_name: str = commands.parameter(description="Name of the class, as used in set_professors"),
                               class_role: discord.Role = commands.parameter(description="Role associated with the class"),
                               forum: discord.ForumChannel = commands.parameter(description="Forum that gets a tag per professor"),
                               lab_forum: discord.ForumChannel | None = commands.parameter(
                                   default=None, description="Optional second forum (e.g. the lab forum) that gets the same tags")) -> None:

        """ Basic command to send prompt for professor and class role assignments """
        # Defer since this can take a while
        await ctx.defer()

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        # No professors configured for this class
        professors = await self.bot.db.get_professors(class_name)
        if not professors:
            await ctx.send(f"There are no professors configured for \"{class_name}\"! Use `set_professors` first.")
            return

        # Each professor becomes a forum tag, and Discord caps tag names at 20 characters
        too_long = [prof for prof in professors if len(prof) > MAX_TAG_NAME_LENGTH]
        if too_long:
            await ctx.send(f"These professor names are longer than {MAX_TAG_NAME_LENGTH} characters and can't be forum tags: "
                           f"{', '.join(too_long)}. Shorten them (e.g. last name only) with `set_professors`.")
            return

        forums = [forum] if lab_forum is None or lab_forum == forum else [forum, lab_forum]

        # Check every forum's tag limit before changing anything, so a failure leaves the server untouched
        plans = {f: self.plan_forum_tags(f, professors) for f in forums}
        for f, (missing, stale) in plans.items():
            if len(f.available_tags) + len(missing) > MAX_FORUM_TAGS:
                await ctx.send(f"Adding tags for {', '.join(missing)} would put {f.mention} over Discord's limit of "
                               f"{MAX_FORUM_TAGS} tags per forum. Delete unused tags in its settings first"
                               + (f" (these match no current professor: {', '.join(stale)})." if stale else "."))
                return

        # Set up the professors' roles and each forum's professor tags
        await self.setup_professor_roles(class_name, professors, ctx.guild)
        try:
            for f, (missing, _) in plans.items():
                await self.apply_forum_tags(f, missing, class_name)
        except discord.HTTPException:
            logging.exception(f"Could not edit the forum tags for {class_name}")
            await ctx.send("Could not edit the forum tags. Make sure the bot can manage those forum channels.")
            return

        # Go through the professors and create the select menu
        view = discord.ui.View(timeout=None)
        prof_select = ProfSelect(class_name, class_role.id, professors)
        view.add_item(prof_select)

        await ctx.send(prompt, view=view)

        # Report the forum changes to the officer only
        lines = []
        for f, (missing, stale) in plans.items():
            line = f"{f.mention}: " + (f"added tags {', '.join(missing)}." if missing else "all professors already had tags.")
            if stale:
                line += f" These tags don't match a current professor: {', '.join(stale)}."
            lines.append(line)
        if any(stale for _, stale in plans.values()):
            lines.append(f"Delete tags you no longer need in the forum's settings (the limit is {MAX_FORUM_TAGS} per forum).")
        await ctx.send("\n".join(lines), ephemeral=True)


    @commands.hybrid_command(description="Basic command to assign pronouns roles")
    @commands.has_any_role("TAO Officer")
    async def send_pronouns_prompt(self, ctx: Context,
                                  she_her_role:          discord.Role = commands.parameter(description="Role to assign for she/her pronouns"),
                                  he_him_role:           discord.Role = commands.parameter(description="Role to assign for he/him pronouns"),
                                  they_them_role:        discord.Role = commands.parameter(description="Role to assign for they/them pronouns"),
                                  any_pronouns_role:     discord.Role = commands.parameter(description="Role to assign for any pronouns"),
                                  other_pronouns_role:   discord.Role = commands.parameter(description="Role to assign for other pronouns"),
                                  ) -> None:
        
        """ Basic command to assign pronouns roles """

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        role_ids = [she_her_role.id, he_him_role.id, they_them_role.id, any_pronouns_role.id, other_pronouns_role.id]

        # Stored so the menu still knows its roles after a restart (they don't fit in the custom_id)
        await self.bot.db.set_config(PRONOUN_ROLES_KEY, ",".join(str(role_id) for role_id in role_ids))

        view = discord.ui.View(timeout=None)
        view.add_item(PronounsSelect(ctx.guild.id, role_ids))

        await ctx.send("Select your pronouns!", view=view)


    @commands.hybrid_command(description="Basic command to assign PT roles, change username, and inform the user of their new Discord roles")
    @commands.has_any_role("TAO Officer")
    async def make_pt(self, ctx: Context,
                      pt: discord.Member = commands.parameter(description="The user who is getting PT roles"),
                      class_role: discord.Role = commands.parameter(description="The class specific PT role(s)"),
                      real_name : str = commands.parameter(default=None, description="The real name of the PT")) -> None:
        
        """ Basic command to assign PT roles, change username, and inform the user of their new Discord roles """
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        # Assign PT role
        pt_role = discord.utils.get(ctx.guild.roles, name="PT")
        if pt_role is not None and pt_role not in pt.roles:
            await pt.add_roles(pt_role)

        # Assign class role
        if class_role not in pt.roles:
            await pt.add_roles(class_role)

        # Change name
        if real_name is not None:
            # Trim the name so the nickname stays within Discord's limit
            suffix = " | PT"
            name = real_name.strip()[:MAX_NICKNAME_LENGTH - len(suffix)].rstrip()
            await pt.edit(nick=f"{name}{suffix}")

        # Notify the PT and remind the officer to manually assign professor roles
        await ctx.send(f"\n<@{ctx.author.id}>, please remember to manually assign them their professor roles if they are supposed to have any!", ephemeral=True)
        
        # Log the command invokation in the bot-log channel
        log_channel_id = await self.bot.db.get_config_id("pt_log_channel")
        channel = self.bot.get_channel(log_channel_id) if log_channel_id is not None else None
        if isinstance(channel, discord.TextChannel):
            await channel.send(f"<@{ctx.author.id}> (ID: {ctx.author.id}) has applied PT roles to <@{pt.id}> (ID: {pt.id})")


    async def setup_professor_roles(self, class_name: str, professors: list[str], guild: discord.Guild) -> list[str]:
        """
        Helper function to set up the professors' roles, returning the role names

        :param str class_name: Name of the class
        :param list[str] professors: The list of professor names for the class
        :param discord.Guild guild: The Guild object representing the server
        """
        role_names = []

        # Go through each professor and create the role if needed
        for professor in professors:
            role_name = class_name.split(" ")[1] + " " + professor

            # Create role if role is not pre-existing
            if not discord.utils.get(guild.roles, name=role_name):
                await guild.create_role(name=role_name)

            role_names.append(role_name)

        return role_names
        
    @staticmethod
    def plan_forum_tags(forum: discord.ForumChannel, professors: list[str]) -> tuple[list[str], list[str]]:
        """
        Compares a forum's tags with the professor list (case-insensitive) without changing anything

        :param discord.ForumChannel forum: The forum whose tags are checked
        :param list[str] professors: The list of professor names for the class
        :return: Professors that still need a tag, and existing tags that match no current professor
        """
        existing_names = {tag.name.lower() for tag in forum.available_tags}
        professor_names = {prof.lower() for prof in professors}

        missing = [prof for prof in professors if prof.lower() not in existing_names]
        stale = [tag.name for tag in forum.available_tags if tag.name.lower() not in professor_names]
        return missing, stale

    @staticmethod
    async def apply_forum_tags(forum: discord.ForumChannel, missing: list[str], class_name: str) -> None:
        """
        Adds the missing professor tags and makes posts require a tag. Existing tags are never removed,
        so manually added tags (e.g. "Solved") and tags on old posts are kept.
        """
        if missing or not forum.flags.require_tag:
            await forum.edit(available_tags=list(forum.available_tags) + [discord.ForumTag(name=prof) for prof in missing],
                             require_tag=False,
                             reason=f"Professor tags for {class_name}")

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def switch_pt_roles(self, 
                              ctx: Context,
                              old_role: discord.Role = commands.parameter(description="The role to switch from"),
                              new_role: discord.Role = commands.parameter(description="The role to switch to")) -> None:
        
        """ Basic command to switch everyone with a role with another """

        # Snapshot now so the list can't change between confirming and switching
        members = list(old_role.members)
        if not members:
            await ctx.send(f"Nobody has the \"{old_role.name}\" role!", ephemeral=True)
            return

        view = ConfirmView(ctx.author.id)
        prompt = await ctx.send(f"This will move **{len(members)}** member(s) from \"{old_role.name}\" to \"{new_role.name}\". Continue?",
                                view=view)
        await view.wait()

        if view.value is None:
            await prompt.edit(content="Timed out, no roles were changed.", view=None)
            return
        if not view.value:
            return

        await prompt.edit(content=f"Switching roles for {len(members)} member(s)...")

        failed = []
        for member in members:
            try:
                await member.remove_roles(old_role)
                await member.add_roles(new_role)
            except discord.HTTPException:
                failed.append(member.mention)

        result = f"Moved {len(members) - len(failed)}/{len(members)} member(s) from \"{old_role.name}\" to \"{new_role.name}\"."
        if failed:
            result += f"\nFailed for: {', '.join(failed)}"
        await prompt.edit(content=result)

async def setup(bot):
    await bot.add_cog(Roles(bot))