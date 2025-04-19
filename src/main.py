import asyncio
import logging
import os

import discord
from discord.ext import commands

intent = discord.Intents.default()
intent.messages = True
intent.message_content = True
client = discord.Client(intents=intent)

bot = commands.Bot(command_prefix='!', intents=intent)

# Configure the logger
logger = logging.getLogger('discord.main')
logger.setLevel(logging.INFO)

extensions = [
    "commands.abyssal_damage_mods",
    "commands.implants",
    # "commands.killbucket",
    # "commands.blobfactor",
    # "commands.corp",
    # "commands.heat", # Deactivated due to needing explanation / rework
    # "commands.rolling", # Deactivated due to np-hard and no good limits
    "commands.abyssal_anything",
    # "commands.zkill",
]

for extension in extensions:
    asyncio.run(bot.load_extension(extension))


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.info(f"Failed to sync commands: {e}")


bot.run(os.environ["DISCORD_TOKEN"])
