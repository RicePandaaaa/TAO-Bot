import discord
from discord.ext import commands
from discord.ext.commands import Context


class Roles(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Nested dictionary: {class_name: [[message, class_role], {emoji: roles}, {professor: emoji}]}
        self.student_info = {}

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def send_student_role_prompt(self, ctx: Context, 
                                       prompt: str = commands.parameter(description="The exact prompt the bot will send"), 
                                       class_name: str = commands.parameter(description="The name of the class (for internal linking reasons)"), 
                                       class_role: discord.Role = commands.parameter(default=None, description="The role that students of this class will receive")) -> None:
        """ 
        Sends a bot message with a user provided prompt internally tied to class_name and class_role 
        """

        # Class name already in use
        if class_name in self.student_info.keys():
            return await ctx.send("This class name is already in use!")
        
        message = await ctx.send(f"{prompt}\n")
        self.student_info[class_name] = [[message, class_role], {}, {}]

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def add_professor(self, ctx: Context, 
                            class_name: str = commands.parameter(description="The internal name of the class"), 
                            professor: str = commands.parameter(description="The name of the professor"), 
                            reaction: str = commands.parameter(description="The emoji used for the reaction"), 
                            role: discord.Role = commands.parameter(description="The role in which students of this professor will receive")) -> None:
        """ 
        Adds a professor to a pre-existing class prompt along with an internally connected role 
        """

        # Not an existing class
        if class_name not in self.student_info.keys():
            return await ctx.send(f"\"{class_name}\" does not exist as a class! Please use the `send_student_role_prompt` command to add the prompt!")
        
        class_info = self.student_info[class_name]
        message_info, role_info, prof_info = class_info

        # Already existing professor
        if professor in prof_info.keys():
            return await ctx.send(f"Professor {professor} already exists for this class!")
        
        # Already existing emoji
        if reaction in prof_info.values():
            return await ctx.send(f"`:{reaction}:` is already in use for this class!")
        
        # Add the reaction 
        role_info[reaction] = role
        prof_info[professor] = reaction
        await message_info[0].add_reaction(reaction)

        # Edit the prompt
        professor_role_pairs = "".join([f"\nProfessor {key}: {prof_info[key]}" for key in prof_info])
        await message_info[0].edit(content=message_info[0].content + professor_role_pairs)

        # Send a message and delete
        bot_message = await ctx.send("Done.")
        await bot_message.delete()

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def add_prof_role(self, ctx: Context, 
                            prof_name: str = commands.parameter(description="Name of the professor to be used for the role")) -> None:
        """ 
        Attempts to add a role given the name 
        """

        # Check if role exists
        if discord.utils.get(ctx.guild.roles, name=prof_name):
            await ctx.send(f"The role for Professor {prof_name} already exists!")
        
        else:
            await ctx.guild.create_role(name=prof_name)
            await ctx.send(f"The role for Professor {prof_name} is now created.")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None :
        """ Assigns roles to users based on reactions to certain messages """
        # Check the message reacted to against specific messages that are being monitored
        for class_name in self.student_info.keys():
            class_info = self.student_info[class_name]
            message_id = class_info[0][0].id

            # ID matches
            if message_id == reaction.message.id:
                # Check if the student already has the class role (prevent multiple professors)
                class_role_to_add = class_info[0][1]
                prof_role_to_add = class_info[1][str(reaction.emoji)]
                if self.has_duplicate_roles(class_role_to_add, prof_role_to_add, user):
                    return
                
                # Check for conflicting roles
                if self.has_conflicting_roles(class_role_to_add, user):
                    return

                # Add the roles
                if class_role_to_add is not None:
                    await user.add_roles(class_role_to_add)
                await user.add_roles(prof_role_to_add)

    def has_duplicate_roles(self, class_role: discord.Role, prof_role: discord.Role, user: discord.User) -> bool:
        """ 
        Checks if the user already has either the class or the professor roles to prevent duplicates 
        
        :param discord.Role class_role: The role associated with the entire class
        :param discord.Role prof_role: The role associated with the professor
        :param discord.User user: The user whose roles are being checked
        """

        if class_role is not None and class_role in user.roles:
            return True
        
        if prof_role in user.roles:
            return True
        
        return False
    
    def has_conflicting_roles(self, class_role: discord.Role, user: discord.User) -> bool:
        """ 
        Checks if the user has roles considered to be pre-requisites

        :param discord.Role class_role: The role associated with the entire class
        :param discord.User user: The user whose roles are being checked
        """
        # Only applies to PHYS roles, don't check otherwise
        if "PHYS" not in class_role.name:
            return False
        
        # Check PHYS sections
        last_class_digit = class_role.name.split(" ")[1][-1]
        for user_role in user.roles:
            if "PHYS" in user_role.name and user_role.name.split(" ")[1][-1] != last_class_digit:
                return True
            
        return False


async def setup(bot):
    await bot.add_cog(Roles(bot))