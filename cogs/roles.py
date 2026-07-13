import discord
from discord.ext import commands
from discord.ext.commands import Context

from DiscordSelect import ProfSelect, StudentSelect, announcements_view, review_view


class Roles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
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


    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_tao_review_prompt(self, ctx: Context,
                                        review_role: discord.Role = commands.parameter(description="TAO review role")) -> None:
        
        """ Basic command to show buttons for opting in and out of TAO review roles """

        message = f"For pings regarding TAO reviews, there is \"{review_role.name}\"!\n" \
                  f"The button options below allow you to opt in or opt out this role as stated:\n" \
                  f"- 1) Opt **into** \"{review_role.name}\"\n" \
                  f"- 2) Opt **out of** \"{review_role.name}\"\n"
        await ctx.send(message, view=review_view(review_role))


    @commands.hybrid_command()
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
                       " If you are a professor, please email **anthony.ha.pham@tamu.edu** to verify your faculty status. Do note that **your selection can only be changed by a mod**, so please be very careful which option you choose!", view=view)


    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_prof_prompt(self, ctx: Context,
                               prompt: str = commands.parameter(description="The prompt text"), 
                               class_name: str = commands.parameter(description="Name of the class"),
                               class_role: discord.Role = commands.parameter(description="Role associated with the class")) -> None:
        
        """ Basic command to send prompt for professor and class role assignments """
        # Defer since this can take a while
        await ctx.defer()

        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        # Invalid class name
        category = discord.utils.get(ctx.guild.categories, name=class_name)
        if category is None:
            await ctx.send("This is an invalid class name!")
            return

        # No professors configured for this class
        professors = await self.bot.db.get_professors(class_name)
        if not professors:
            await ctx.send(f"There are no professors configured for \"{class_name}\"! Use `set_professors` first.")
            return

        # Set up the professors' roles and channels
        role_names = await self.setup_professor_roles(class_name, professors, ctx.guild)
        await self.setup_prof_channels(category, role_names, class_role, ctx.guild)

        # Go through the professors and create the select menu
        view = discord.ui.View(timeout=None)
        prof_select = ProfSelect(class_name, class_role.id, professors)
        view.add_item(prof_select)

        await ctx.send(prompt, view=view)

    @commands.hybrid_command()
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
            # New nickname would exceed max
            if len(f"{real_name} | PT") > 32:
                await pt.edit(nick="REAL NAME | PT")
            else:
                await pt.edit(nick=f"{real_name} | PT")

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
        
    async def setup_prof_channels(self, category: discord.CategoryChannel, 
                                  professors: list[str],
                                  class_role: discord.Role,
                                  guild: discord.Guild) -> None:
        """ 
        Helper function to help set up channels for professors

        :param discord.CategoryChannel category: The channel category where the channels will belong
        :param list[str] professors: The list of names of the professors
        :param discord.Role class_role: The role associated with the class the professors teach
        :param discord.Guild guild: The guild associated with the server
        """

        # Go through the professors and generate channels
        for professor in professors:
            # Get the professor role
            professor_role = discord.utils.get(guild.roles, name=professor)

            if professor_role is None:
                continue

            if not discord.utils.get(category.text_channels, name="-".join(professor.split(" ")).lower()):
                # Only allow students of the same professor to view the channel
                officer_role = discord.utils.get(guild.roles, name="TAO Officer")
                overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    class_role: discord.PermissionOverwrite(read_messages=False),
                    professor_role: discord.PermissionOverwrite(read_messages=True),
                }
                if officer_role is not None:
                    overwrites[officer_role] = discord.PermissionOverwrite(read_messages=True)

                await category.create_text_channel(name=professor, overwrites=overwrites)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def switch_pt_roles(self, 
                              ctx: Context,
                              old_role: discord.Role = commands.parameter(description="The role to switch from"),
                              new_role: discord.Role = commands.parameter(description="The role to switch to")) -> None:
        
        """ Basic command to switch everyone with a role with another """

        # Get all members with the old role
        members = old_role.members

        # Switch the roles
        for member in members:
            await member.remove_roles(old_role)
            await member.add_roles(new_role)

async def setup(bot):
    await bot.add_cog(Roles(bot))