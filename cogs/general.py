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
    async def sync(self, ctx: Context, guilds: Greedy[discord.Object] = None, spec: typing.Optional[typing.Literal["~", "*", "^"]] = None) -> None:
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
        
    @commands.hybrid_command(aliases=["chegg", "chatgpt"])
    async def cheating(self, ctx: Context):
        """ Basic command in regards of sus study material sources """
        await ctx.send("Please do not use outside resources such as Chegg and ChatGPT to do your assignments!")
        
    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def addqueuechannel(self, ctx: Context, channel: str, role: str) -> None:
        """ Adds a queue channel associated with a certain role (subject) """

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
        await ctx.send(f'You have set the "{voice_channel.name}" voice channel as a queue channel. Those with the "{subject_role}" role will be able to pull students from that channel into their office hours channel.')

    @commands.hybrid_command()
    @commands.has_any_role('TAO Officer')
    async def setcategory(self, ctx: Context, category_str: str) -> None:
        """ Sets the category to put the office hours channels in """

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
    async def setofficehours(self, ctx: Context, link: str) -> None:
        """ Sets the office hours link """
        self.office_hours = link

async def setup(bot):
    await bot.add_cog(General(bot))
