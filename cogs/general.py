import discord, typing
from discord.ext import commands
from discord.ext.commands import Context, Greedy


class General(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.office_hours = "\"DOES NOT EXIST YET\""

    @commands.hybrid_command()
    @commands.guild_only()
    @commands.has_any_role('TAO Officer')
    async def sync(self, ctx: Context, 
                   guilds: Greedy[discord.Object] = commands.parameter(default=None, description="A list of guilds to go through"), 
                   spec: typing.Optional[typing.Literal["~", "*", "^"]] = commands.parameter(default=None, description="Type of sync to be performed")) -> None:
        """ 
        Syncs the hybrid commands (allows for usage of slash commands), from discord.py server  
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException as error:
                print(error)
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")
    @commands.hybrid_command()
    async def howdy(self, ctx: Context) -> None:
        """ Basic command for obtaining info about the bot """
        
        await ctx.send("Howdy, I was created to assist PTs and professors in managing voice channels for one-on-one " \
                        "sessions for students and content reviews. I can also provide students with information " \
                        "related to office hours! Please type `tao.help` for a complete command list!")

    @commands.hybrid_command(aliases=["oh"])
    async def officehours(self, ctx: Context) -> None:
        """ Basic command redirecting users to the office hours channel (for now) """

        await ctx.send(f"If there is a link to the office hours times, it will be shown here: {self.office_hours}")
        
    @commands.hybrid_command()
    async def cheating(self, ctx: Context) -> None:
        """ Basic command in regards of sus study material sources """

        await ctx.send("Please do not use outside resources such as Chegg and ChatGPT to do your assignments!" \
                       " Also, if you are helping others, do be aware to not share your solutions or to share or say anything" \
                        " that may break the Aggie Honor Code and any rules set by your professor.")

    @commands.hybrid_command()
    async def explain(self, ctx: Context) -> None:
        """ Basic command in case the question is asked is very vague """

        formatting_link = "https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-"
        await ctx.send(f"{ctx.author.display_name} wants to help you, but it seems that your question is rather unclear." \
                       f" For coding questions, please consult <{formatting_link}> to properly show code snippets, but DO NOT SHARE CODE USED IN YOUR SUBMITTED ASSIGNMENTS." \
                        f" Also please provide full error messages for best results (you may explain the error but again, be sure your explanation is clear.)" \
                         f" For any other questions, please provide full context of your problem, including any related images that can help.")
        
    @commands.hybrid_command()
    async def code(self, ctx: Context) -> None:
        """ Basic command warning users against posting code for their HW or other assignments """

        await ctx.send("**DO NOT SHARE ANY PART OF YOUR CODE THAT IS USED IN YOUR SUBMITTED ASSIGNMENTS.**" \
                       " You can only share code that was created for purposes unrelated to your assignments." \
                        " Posting your code used in assignments (such as labs and HW) can and will lead to severe consequences.")
        
    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def addqueuechannel(self, ctx: Context, 
                              channel: str = commands.parameter(default="The channel ID of the voice channel to be added"), 
                              role: str = commands.parameter(default="The role ID of the role to be added")) -> None:
        """ 
        Adds a queue channel associated with a certain role (subject) 
        """

        channel_id, role_id = int(channel), int(role)

        # Validate channel
        voice_channel = discord.utils.get(ctx.guild.voice_channels, id=channel_id)
        if voice_channel is None:
            return await ctx.send("Please enter a valid voice channel ID!")
            
        
        # Validate role
        subject_role = discord.utils.get(ctx.guild.roles, id=role_id)
        if subject_role is None:
            return await ctx.send("Please enter a valid role!")
            
        vc_cog = self.bot.get_cog("VoiceChannel")
        vc_cog.add_queue_channel(channel_id, role_id)

        # Confirm to the user
        await ctx.send(f'You have set the "{voice_channel.name}" voice channel as a queue channel. PTs with the "{subject_role}" role will be able to pull students from that channel into their office hours channel.')

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def setcategory(self, ctx: Context, 
                          category_str: str = commands.parameter(description="The category ID where all the office hours channels will be created.")) -> None:
        """ 
        Sets the category to put the office hours channels in 
        """

        category_id = int(category_str)

        # Validate category
        category = discord.utils.get(ctx.guild.categories, id=category_id)
        if category is None:
            await ctx.send("Please enter a valid voice channel ID!")

        vc_cog = self.bot.get_cog("VoiceChannel")
        vc_cog.set_category(category_id)

        # Confirm to the user
        await ctx.send(f'You have set the "{category.name}" category to be where office hours voice channels will be created.')

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def joinvc(self, ctx: Context) -> None:
        """ Forces the bot to enter the voice channel in which the user is currently in """

        await ctx.author.voice.channel.connect()
        await ctx.send(f"Successfully joined, <#{ctx.author.voice.channel.id}>!")

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def leavevc(self, ctx: Context) -> None:
        """ Forces the bot to gracefully leave the voice channel """
        
        await ctx.voice_client.disconnect()
        await ctx.send(f"Successfully left the voice channel!")

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def setofficehours(self, ctx: Context, 
                             link: str = commands.parameter(description="Link to the office hours spreadsheet")) -> None:
        """ 
        Sets the office hours link 
        """

        self.office_hours = link

async def setup(bot):
    await bot.add_cog(General(bot))
