import discord, csv, asyncio
from discord.ext import commands
from discord.ext.commands import Context

from DiscordSelect import ProfSelect, YearSelect


class Roles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_welcome_prompt(self, ctx: Context, 
                                  freshman_role:       discord.Role = commands.parameter(description="Role to assign to freshmen"),
                                  sophomore_role:      discord.Role = commands.parameter(description="Role to assign to sophomores"),
                                  junior_role:         discord.Role = commands.parameter(description="Role to assign to juniors"),
                                  senior_role:         discord.Role = commands.parameter(description="Role to assign to seniors"),
                                  super_senior_role:   discord.Role = commands.parameter(description="Role to assign to super seniors"),
                                  guest_role:          discord.Role = commands.parameter(description="Role to assign to guests"),
                                  former_student_role: discord.Role = commands.parameter(description="Role to assign to former students")) -> None:
        
        """ Basic command to send welcome prompt and assign roles """

        view = discord.ui.View()
        year_select_menu = YearSelect(["Freshman", "Sophomore", "Junior", "Senior", "Super Senior", "Guest", "Former Student"],
                                      [freshman_role, sophomore_role, junior_role, senior_role,
                                       super_senior_role, guest_role, former_student_role])
        view.add_item(year_select_menu)

        await ctx.send("Welcome to the TAO server! If you have not already, please **read the newcomer tips at " \
                       "<#1144274416965013565> and the server guidelines at <#1023087608928153681>**. Also, please select what type of student " \
                       "you are. Guests and former students do have a role as well, so please choose even if you are not a student. "\
                       " If you are a professor, please email **taoengr@gmail.com** to verify your faculty status." \
                       " Do note that **your selection can only be changed by a mod**, so please be very careful which option you choose!", view=view)


    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_prof_prompt(self, ctx: Context,
                               prompt: str = commands.parameter(description="The prompt text"), 
                               class_name: str = commands.parameter(description="Name of the class"),
                               class_role: discord.Role = commands.parameter(description="Role associated with the class")) -> None:
        
        """ Basic command to send prompt for professor and class role assignments """
        # Defer since this can take a while
        await ctx.defer()

        # Invalid class name
        category = discord.utils.get(ctx.guild.categories, name=class_name)
        if category is None:
            return await ctx.send("This is an invalid class name!")

        # Set up professors and their roles and channels
        professors = await self.setup_professor_roles(class_name, ctx.guild)
        await self.setup_prof_channels(category, professors, class_role, ctx.guild)

        # Set up the view and the prompt
        view = discord.ui.View()
        roles = [discord.utils.get(ctx.guild.roles, name=professor) for professor in professors]
        prof_select = ProfSelect(professors, roles, class_name, class_role)
        view.add_item(prof_select)

        await ctx.send(prompt, view=view)


    async def setup_professor_roles(self, class_name: str, guild: discord.Guild) -> list[str]:
        """ 
        Helper function to set up the professors and their roles 
        
        :param str class_name: Name of the class
        :param discord.Guild guild: The Guild object representing the server
        """
        professors = []

        # Try to open the file if it exists
        try:
            with open(f"cogs/{class_name}.csv", "r") as csv_file:
                csv_reader = csv.reader(csv_file)

                # Go through each professor and create the role if needed
                for row in csv_reader:
                    professor = row[0]

                    # Skip if placeholder value found
                    if professor == "TBD": continue

                    # Skip if the professor is a repeat
                    if professor in professors: continue

                    # Create role if role is not pre-existing
                    if not discord.utils.get(guild.roles, name=professor):
                        await guild.create_role(name=professor)

                    professors.append(professor)

            professors.sort()
            return professors

        # File doesn't exist
        except:
            return professors
        
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

            if not discord.utils.get(category.text_channels, name=professor.lower()):
                # Only allow students of the same professor to view the channel
                officer_role = discord.utils.get(guild.roles, name="TAO Officer")
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    class_role: discord.PermissionOverwrite(read_messages=False),
                    professor_role: discord.PermissionOverwrite(read_messages=True),
                    officer_role: discord.PermissionOverwrite(read_messages=True)
                }

                await category.create_text_channel(name=professor, overwrites=overwrites)



async def setup(bot):
    await bot.add_cog(Roles(bot))