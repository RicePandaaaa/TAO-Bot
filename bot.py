import asyncio, os, discord, logging
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(intents=intents, command_prefix="tao.", activity=discord.Game(name="tao.help"))

READY_CHANNEL_ID = int(os.environ['READY_CHANNEL_ID'])
TOKEN = str(os.environ['TOKEN'])

"""
Just a cute message to let me know the bot is on/
"""
@bot.event
async def on_ready():
    channel = bot.get_channel(READY_CHANNEL_ID)

    await channel.send("Howdy Anthony! The bot is ready to go!")

"""
Add two roles to users everytime someone joins
"""
@bot.event
async def on_member_join(member):
    server_role = discord.utils.get(member.guild.roles, id=1147655175209754764)
    board_role = discord.utils.get(member.guild.roles, id=1147655249784492113)
    await member.add_roles(server_role, board_role)

"""
Load the bot with cogs
"""
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())
