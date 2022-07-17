from datetime import datetime
from utils import lookup
import asyncio
import aiohttp
import ssl
import certifi
import json


# Functions to get a kill from esi
async def get_kill(session, id, hash, start, data, over):
    async with session.get(f"https://esi.evetech.net/latest/killmails/{id}/{hash}/?datasource=tranquility") as resp:
        try:
            kill = await resp.json(content_type=None)
            if "killmail_time" in kill:
                time = datetime.strptime(kill['killmail_time'], '%Y-%m-%dT%H:%M:%SZ')
                if start < time:
                    data.append(kill)
                else:
                    over.append(kill)
        except json.decoder.JSONDecodeError:
            await get_kill(session, id, hash, start, data, over)


# Function to get all kills from a zkb link in timeframe
async def gather_kills(zkill_url, start):
    # Workaround for aiohttp not coming with certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    data = []
    over = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        page = 1
        while len(over) == 0 and page < 100:
            async with session.get(f"{zkill_url}page/{page}/") as response:
                try:
                    kills = await response.json(content_type=None)
                except json.decoder.JSONDecodeError:
                    continue  # We just try again

                if type(kills) is dict:
                    tasks = [get_kill(session, *kill, start, data, over) for kill in kills.items()]
                else:
                    tasks = [get_kill(session, kill["killmail_id"], kill["zkb"]["hash"], start, data, over) for kill in
                             kills]

                await asyncio.gather(*tasks)
                page += 1
    return data


async def command_blobfactor(arguments, message):

    if "help" in arguments:
        await message.channel.send(
            "Usage:\n!killbucket\n"
            "<character_name>|<character_id> |\n"
            "-c|--corporation <corporation_name>|<corporation_id>\n"
            "-a|--alliance <alliance_name>|<alliance_id>\n"
            "[-d|--days <days_to_querry> | --alltime]"
        )
        return

    # Config
    character_days = 180
    corporation_days = 30
    alliance_days = 14

    if "alliance" in arguments or "a" in arguments:
        name = " ".join(arguments["a"] if "a" in arguments else arguments["alliance"])
        id = lookup(name, 'alliances')
        querry = "allianceID"
        days = alliance_days
    elif "corporation" in arguments or "c" in arguments:
        name = " ".join(arguments["c"] if "c" in arguments else arguments["corporation"])
        id = lookup(name, 'corporations')
        querry = "corporationID"
        days = corporation_days
    else:
        name = " ".join(arguments[""])
        id = lookup(name, 'characters')
        querry = "characterID"
        days = character_days

    if "days" in arguments:
        days = int(arguments["days"][0])
    elif "d" in arguments:
        days = int(arguments["d"][0])

    until = datetime.utcnow() - datetime(days=days)

    if "alltime" in arguments:
        until = datetime(2003, 5, 6, 0, 0)  # Eve release date
        days = (datetime.utcnow() - until).days

    friendlies = []
    kills = await gather_kills(f"https://zkillboard.com/api/kills/{querry}/{id}/kills/",  until)
    for kill in kills:
        friendlies.extend(kill['attackers'])

    enemies = []
    losses = await gather_kills(f"https://zkillboard.com/api/kills/{querry}/{id}/losses/", until)
    for loss in losses:
        enemies.extend(loss['attackers'])

    if "thirdparty" in arguments and arguments["thirdparty"] == ["no"]:
        friendlies = [f for f in friendlies if "corporation_id" in f and f["corporation_id"] == 98633005]
        enemies = [e for e in enemies if "corporation_id" in e and e["corporation_id"] != 98633005]

    await message.channel.send(
        f"**{name}'s last {days} days ** (analyzed {len(kills)} kills and {len(losses)} losses) \n"
        f"Average Pilots on kill: {len(friendlies) / len(kills) :.2f}\n"
        f"Average Enemies on loss: {len(enemies) / len(losses) :.2f}\n"
        f"Blob Factor: {len(friendlies) / len(kills) * len(losses) / len(enemies) :.2f}"
    )
