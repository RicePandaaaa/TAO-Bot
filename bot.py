import asyncio, os, discord, logging, dotenv
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(intents=intents, command_prefix="tao.", activity=discord.Game(name="tao.help"))
dotenv.load_dotenv(dotenv_path="bot.env")

READY_CHANNEL_ID = int(os.getenv('READY_CHANNEL_ID'))
TOKEN = str(os.getenv('TOKEN'))

"""
Just a cute message to let me know the bot is on/
"""
@bot.event
async def on_ready():
    channel = bot.get_channel(READY_CHANNEL_ID)

    await channel.send("Howdy Anthony! The bot is ready to go!")

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
