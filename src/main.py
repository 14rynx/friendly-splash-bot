import asyncio
import os

import discord
from discord.ext import commands

intent = discord.Intents.default()
intent.messages = True
intent.message_content = True
client = discord.Client(intents=intent)

bot = commands.Bot(command_prefix='!', intents=intent)

extensions = [
    "commands.abyssal_damage_mods",
    "commands.implants",
    # "commands.killbucket",
    # "commands.blobfactor",
    # "commands.corp",
    # "commands.heat", # Deactivated due to needing explanation / rework
    # "commands.rolling", # Deactivated due to np-hard and no good limits
    "commands.stonks",
    "commands.teams",
    "commands.abyssal_anything",
    # "commands.zkill",
]

for extension in extensions:
    asyncio.run(bot.load_extension(extension))

bot.run(os.environ["DISCORD_TOKEN"])
