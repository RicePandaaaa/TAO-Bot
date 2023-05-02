import asyncio, os, discord, logging
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(intents=intents, command_prefix="!")

READY_CHANNEL_ID = 
TOKEN = 

"""
Just a cute message to let me know the bot is on/
"""
@bot.event
async def on_ready():
    channel = bot.get_channel(READY_CHANNEL_ID)

    await channel.send("Hey Tony, I'm all ready to go! o7")

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
