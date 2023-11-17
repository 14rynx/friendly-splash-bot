import asyncio
import json

import discord
from discord.ext import commands

with open('secrets.json', "r") as f:
    TOKEN = json.loads(f.read())["TOKEN"]

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
]

for extension in extensions:
    asyncio.run(bot.load_extension(extension))

bot.run(TOKEN)
