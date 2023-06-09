import discord
from discord.ext import commands
from discord.ext.commands import Context


class VoiceChannel(commands.Cog):

    def __init__(self, bot):
        self.channel_number = 0
        self.bot = bot

        self.queue_channels = {}
        self.pt_roles = []
        self.voice_channels = []
        self.office_hours_category = None
        self.queue = {}
        
    @commands.hybrid_command(aliases=["ohvc"])
    async def create_office_hours_vc(self, ctx: Context, room_size: int=2):
        """ Creates a voice channel for office hours """

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
        vc_cat = discord.utils.get(ctx.guild.categories, id=1070134666260140032)
        voice_channel = await discord.Guild.create_voice_channel(ctx.guild, name=vc_name, reason=vc_reason, category=vc_cat, user_limit=room_size)
        
        # Add the voice channel to the list and add the user to the vc
        self.voice_channels.append(voice_channel)
        await ctx.author.move_to(voice_channel)
        await ctx.send("Room created successfully!")
        self.channel_number += 1

    @commands.hybrid_command(aliases=["cq", "queue"])
    async def check_queue(self, ctx: Context):
        """ Outputs the first ten people in queue and the user's current position, if in queue """

        vc = ctx.author.voice.channel
        if vc is None:
            return await ctx.send("You must be in a voice channel!")
        
        # Voice channel is not a queue channel
        if vc.id not in self.queue:
            return await ctx.send(f"{ctx.author.voice.channel.name} is not a valid queue voice channel!")
        
        # Empty queue
        if len(self.queue[vc.id]) == 0:
            return await ctx.send("The queue is currently empty.")

        else:
            output = ""
            place = -1
            for index, member in enumerate(self.queue[vc.id], start=1):
                output += f"{index}. {member.name}\n"

                # Save place if user is found in queue
                if member.id == ctx.author.id:
                    place = index
                
                # Stop once ten people are processed
                if index == 10:
                    break

            # Output
            placement = f"\nYour current position in queue is: **{place}**."
            await ctx.send(output + placement)

    @commands.hybrid_command()
    async def grab_next(self, ctx: Context):
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

        # Empty queue
        for channel_id in self.queue_channels:
            # If channel i
            if len(self.queue) == 0:
                return await ctx.send("The queue is empty.")
        

        await self.queue[0].move_to(vc)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """ Deletes inactive office hours voice channels and updates the queue """

        # Check for empty office hours voice channels
        for index in range(len(self.voice_channels) - 1, -1, -1):
            channel = self.voice_channels[index]

            # Empty voice channel
            if len(channel.voice_states) == 0:
                self.voice_channels.pop(index)

                # Update max channel number
                if index == self.channel_number - 1:
                    self.channel_number -= 1

                await channel.delete()

        # Add user to the queue
        if after is not None and after.channel is not None and after.channel.id in self.queue_channels:
            self.queue_channels[after.channel.id].append(member)

        # Remove user from the queue
        if before is not None and before.channel is not None and before.channel.id in self.queue_channels:
            self.queue_channels[before.channel.id].remove(member)

    def add_queue_channel(self, channel_id: int, role_id: int) -> None:
        self.queue_channels[channel_id] = role_id
        self.pt_roles.append(role_id)
        self.queue[channel_id] = []

    def set_category(self, category: id) -> None:
        self.office_hours_category = category

    def is_pt(self, roles) -> bool:
        for role in roles:
            if role.id in self.pt_roles:
                return True
            
        return False
        

async def setup(bot):
    await bot.add_cog(VoiceChannel(bot))
    