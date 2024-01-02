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
    "commands.damage_mods.damage_mods",
    "commands.implants.implants",
    "commands.killbucket.killbucket",
    "commands.blobfactor",
    "commands.corp",
    "commands.heat",
    "commands.rolling",
    "commands.stonks",
    "commands.teams",
    "commands.multi_abyssals.multi"
]

for extension in extensions:
    asyncio.run(bot.load_extension(extension))

bot.run(os.environ["DISCORD_TOKEN"])
