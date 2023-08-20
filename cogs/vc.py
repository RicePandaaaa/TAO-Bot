import discord
from discord.ext import commands
from discord.ext.commands import Context


class VoiceChannel(commands.Cog):

    def __init__(self, bot):
        self.channel_number = 1
        self.bot = bot

        self.queue_channels = {1131342483352211526: 1142822139506983043, 
                               1131342621671956512: 1142822128438235146,
                               1131342752743948438: 1142821958925426749,
                               1133390683554713664: 1142822132942913597,
                               1133390590613131404: 1142822135568547892}             
        self.queue = {}

        self.pt_roles = [1142822139506983043, 1142822128438235146, 1142822128438235146, 1142822132942913597, 1142822135568547892]           
        self.pt_voice_channels = []     
        self.office_hours_category = 1131343906320154704
        
    @commands.hybrid_command(aliases=["ohvc"])
    @commands.has_any_role("Current PT")
    async def create_office_hours_vc(self, ctx: Context, room_size: int=2) -> None:
        """ 
        Creates a voice channel for office hours 
        
        :param int room_size: The maximum number of users allowed in a room (defaults to 2)
        """

        # Checks if the user is a valid PT
        if not self.is_pt(ctx.author.roles):
            return await ctx.send("Only PTs can use this command!")

        # Check user is in voice channel
        if ctx.author.voice is None:
            return await ctx.send("You need to be in a voice channel first.")

        # Validate the room size
        if room_size < 2 or room_size > 99:
            return await ctx.send("If specifying the room size, the size must be between 2 and 99, inclusive.")

        # Create the voice channel
        vc_name = f"Office Hours {self.channel_number}"
        vc_reason = f"{ctx.author.display_name} has requested to make a voice channel."
        vc_cat = discord.utils.get(ctx.guild.categories, id=self.office_hours_category)
        voice_channel = await discord.Guild.create_voice_channel(ctx.guild, name=vc_name, reason=vc_reason, category=vc_cat, user_limit=room_size)
        
        # Add the voice channel to the list and add the user to the vc
        self.pt_voice_channels.append(voice_channel)
        await ctx.author.move_to(voice_channel)
        await ctx.send("Room created successfully!")
        self.channel_number += 1

    @commands.hybrid_command(aliases=["cq", "queue"])
    async def check_queue(self, ctx: Context) -> None:
        """ Outputs the first ten people in queue and the user's current position, if in queue """

        vc = ctx.author.voice.channel
        if vc is None:
            return await ctx.send("You must be in a voice channel!")
        
        # Voice channel is not a queue channel
        if vc.id not in self.queue_channels:
            return await ctx.send(f"{ctx.author.voice.channel.name} is not a valid queue voice channel!")
        
        # Output positions (overall and channel-specific)
        students_in_queue = list(self.queue.keys())
        overall_position = 1 + students_in_queue.index(ctx.author.id)
        channel_position = overall_position

        for i in range(overall_position):
            student = students_in_queue[i]
            
            # If person in front of overall queue is not in same channel, decrememnt channel position by one
            if self.queue[student] != self.queue[ctx.author.id]:
                channel_position -= 1

        # Output the results to the person
        subject_name = vc.name[:-6]
        await ctx.send(f"Your overall position in the queue is: {overall_position}. Your position in the queue for '{subject_name}' is: {channel_position}")



    @commands.hybrid_command()
    @commands.has_any_role("Current PT")
    async def grab_next(self, ctx: Context) -> None:
        """ Moves the next person in the queue to the user's current voice channel """

        # Checks if the user is a valid PT
        if not self.is_pt(ctx.author.roles):
            return await ctx.send("Only PTs can use this command!")
        
        # Check for valid voice channel
        vc = ctx.author.voice.channel
        if vc is not None and not vc.name.startswith("Office Hours"):
            return await ctx.send("You must be in an office hours voice channel to use this command.")
        if vc is not None and len(vc.members) == vc.user_limit:
            return await ctx.send("Your room is full!")

        # Check in the main queue
        for member_id in self.queue:
            pt_role_id = self.queue_channels[self.queue[member_id]]
            pt_role = ctx.author.guild.get_role(pt_role_id)

            # If the student needs help in a subject the PT can help with, pull them in
            if pt_role in ctx.author.roles:
                member = ctx.author.guild.get_member(member_id)
                await member.move_to(vc)
                await ctx.send(f"<@{member_id}> has been pulled into <#{vc.id}> led by PT <@{ctx.author.id}>")
            
        # No valid students in queue
        await ctx.send("There are no students in queue that you can help with!")

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def remove_queue(self, ctx: Context, channel_id: str) -> None:
        """ 
        Removes a voice channel from the list of queues 
        
        :param str channel_id: The channel ID of the voice channel to be removed
        """
        # Check if the channel even is a queue channel
        if int(channel_id) not in self.queue_channels.keys():
            return await ctx.send(f"The channel with id \"{channel_id}\" is not a queue voice channel!")
    
        del self.queue_channels[int(channel_id)]
        await ctx.send(f"The channel with id \"{channel_id}\" has been removed!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """ Deletes inactive office hours voice channels and updates the queue """

        # Check for empty office hours voice channels
        for index in range(len(self.pt_voice_channels) - 1, -1, -1):
            channel = self.pt_voice_channels[index]

            # Empty voice channel
            if len(channel.voice_states) == 0:
                self.pt_voice_channels.pop(index)

                # Update max channel number
                if index == self.channel_number - 2:
                    self.channel_number -= 1

                # Remove the channel
                await channel.delete()

        # Remove user from the queue
        if before is not None and before.channel is not None and before.channel.id in self.queue_channels:
            del self.queue[member.id]

        # Add user to queue and assign user to queue channel
        if after is not None and after.channel is not None and after.channel.id in self.queue_channels:
            self.queue[member.id] = after.channel.id

    def add_queue_channel(self, channel_id: int, role_id: int) -> None:
        """ 
        Adds a channel as queue alongside the relevant PT role 
        
        :param int channel_id: The channel ID of the voice channel to be added
        :param int role_id: The role ID of the associated role
        """

        self.queue_channels[channel_id] = role_id
        self.pt_roles.append(role_id)

    def set_category(self, category: id) -> None:
        """ Sets the ID of the category to include office hours channels"""

        self.office_hours_category = category

    def is_pt(self, roles: list[discord.Role]) -> bool:
        """ 
        Checks if the person has any roles for PT 
        
        :param list[discord.Role] roles: The list of user roles to check"""
        
        for role in roles:
            if role.id in self.pt_roles:
                return True
            
        return False
        

async def setup(bot):
    await bot.add_cog(VoiceChannel(bot))
    