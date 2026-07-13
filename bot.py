import asyncio, os, discord, logging
from discord.ext import commands

from db import Database
from DiscordSelect import AnnouncementsButton, ReviewButton, StudentSelect, ProfSelect

# Remove this once the bot is deployed
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logging.basicConfig(level=logging.INFO)


class TAOBot(commands.Bot):
    def __init__(self):
        super().__init__(intents=intents, command_prefix="tao.", activity=discord.Game(name="tao.help"))
        self.db = Database()

    async def setup_hook(self):
        await self.db.init()

        # Buttons/selects survive restarts: their state lives in their custom_ids
        self.add_dynamic_items(AnnouncementsButton, ReviewButton, StudentSelect, ProfSelect)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

    async def close(self):
        await self.db.close()
        await super().close()


bot = TAOBot()

READY_CHANNEL_ID = int(os.environ['READY_CHANNEL_ID'])
TOKEN = str(os.environ['TOKEN'])

"""
Just a message to let me know the bot is on
"""
@bot.event
async def on_ready():
    channel = bot.get_channel(READY_CHANNEL_ID)

    if channel and isinstance(channel, discord.TextChannel):
        await channel.send("Howdy! The bot is ready to go!")
    else:
        logging.warning("READY_CHANNEL_ID is not a valid text channel ID!")

"""
Add two roles to users everytime someone joins
"""
@bot.event
async def on_member_join(member):
    for key in ("welcome_role_1", "welcome_role_2"):
        role_id = await bot.db.get_config_id(key)
        role = discord.utils.get(member.guild.roles, id=role_id) if role_id is not None else None

        if role is None:
            logging.warning(f"Welcome role \"{key}\" is unset or no longer exists, skipping!")
            continue

        await member.add_roles(role)


async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
