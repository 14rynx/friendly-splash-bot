import asyncio
import logging
import ssl
from datetime import datetime, timedelta

import aiohttp
import certifi
from discord.ext import commands
from utils import lookup, gather_kills

# Configure the logger
logger = logging.getLogger('discord.corp')
logger.setLevel(logging.INFO)


async def get_corp_name(corporation_id, session):
    async with session.get(f"https://esi.evetech.net/latest/corporations/{corporation_id}/") as response:
        return (await response.json(content_type=None))[
            "name"] if response.status == 200 else f"Could not load corp name for {corporation_id}"


async def get_corp_member_count(corporation_id, session):
    async with session.get(f"https://esi.evetech.net/latest/corporations/{corporation_id}/") as response:
        return (await response.json(content_type=None))[
            "member_count"] if response.status == 200 else f"Could not load corp member count for {corporation_id}"


async def get_character_corporation(character_id, session):
    async with session.get(f"https://esi.evetech.net/latest/characters/{character_id}/") as response:
        return (await response.json(content_type=None))["corporation_id"] if response.status == 200 else 0


async def get_corp_statistics(corporation_id):
    days = 30

    # Gather Data from API
    kills = await gather_kills(f"https://zkillboard.com/api/kills/corporationID/{corporation_id}/kills/",
                               datetime.utcnow() - timedelta(days=days))
    losses = await gather_kills(f"https://zkillboard.com/api/kills/corporationID/{corporation_id}/losses/",
                                datetime.utcnow() - timedelta(days=days))

    # Count Friendlies
    friendlies = 0
    for kill in kills:
        friendlies += len(kill['attackers'])
    avg_friendlies = friendlies / (len(kills)) if len(kills) > 0 else 1

    # Count Enemies
    enemies = 0
    for loss in losses:
        enemies += len(loss['attackers'])
    avg_enemies = enemies / (len(losses)) if len(losses) > 0 else 1

    # Count Nanos / Polys
    nanos = 0
    for loss in losses:
        for item in loss['victim']['items']:
            if item["item_type_id"] in [1242, 14127, 2603, 2605, 15813, 21500,
                                        5599]:  # All types of Nanofiber Internal Structure
                nanos += 1
            if item["item_type_id"] in [31177, 31183, 31179, 31185, 26070, 26312]:  # All types of Polycarbons
                nanos += 1
    avg_nanos = nanos / (len(losses)) if len(losses) > 0 else 0

    # Map Kills by hour of day
    hour_map = {}
    for item in kills + losses:
        if "killmail_time" in item:
            date = datetime.strptime(item['killmail_time'], '%Y-%m-%dT%H:%M:%SZ')
            if date.hour in hour_map:
                if not date.day in hour_map[date.hour]:
                    hour_map[date.hour].append(date.isoformat())
            else:
                hour_map.update({date.hour: [date.isoformat()]})

    # Filter for active hours
    activity = [len(hour_map.get(hour, [])) for hour in range(24)]

    # Do one convolutional pass to for smoothing
    activity = [
        activity[hour - 2] + 2 * activity[hour - 1] + 3 * activity[hour] + 2 * activity[hour - 23] + activity[hour - 22]
        for hour in range(24)]
    th = sum(activity) / 18
    hours = [x for x, a in enumerate(activity) if a > th]

    # Group Active Hours
    start = 0
    on = False
    zones = []
    for x in range(25):
        if x in hours and not on:
            start = x
            on = True
        elif x not in hours and on:
            zones.append([start, x - 1])
            on = False

    # Connect 23-0
    if zones and zones[0][0] == 0 and zones[-1][1] == 23:
        zones[0][0] = zones[-1][0]
        zones.pop()

    # Build Timezone string representation
    timezone_string = ""
    for z in zones:
        if z[0] == z[1]:
            timezone_string += f"[{z[0]}]"
        elif z[0] < z[1]:
            timezone_string += f"[{z[0]}-{z[1]}]"
        else:
            timezone_string += f"[{z[0]}->{z[1]}]"

    if timezone_string == "":
        timezone_string = "[ANY]"

    # Build list of active characters
    character_set = set()
    for kill in kills:
        for attacker in kill["attackers"]:
            if "character_id" in attacker:
                character_set.add(attacker["character_id"])

    for loss in losses:
        if "character_id" in loss['victim']:
            character_set.add(loss['victim']["character_id"])

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        # Count characters that are in this corp
        tasks = [get_character_corporation(character, session) for character in character_set]
        character_corps = await asyncio.gather(*tasks)
        active_characters = sum([1 for c in character_corps if (c == corporation_id)])

        name = await get_corp_name(corporation_id, session)
        total_characters = await get_corp_member_count(corporation_id, session)
    return f"**{name}'s last {days} Days** \n Timezone: {timezone_string} \n Active Characters: {active_characters}/{total_characters} \n Average Nanos on Ships: {avg_nanos:.2f}\n Average Fleet Size on Killmail: {avg_friendlies:.2f} \n Average Enemy Fleet Size on Killmail: {avg_enemies:.2f} \n Blob Factor: {avg_friendlies / avg_enemies:.2f}"


@commands.command()
async def corp(ctx, *args):
    """
    !corp <corporation_name> | <corporation_id>
    """
    logger.info(f"{ctx.author.name} used !corp {args}")
    try:
        name = " ".join(args)
        id = lookup(name, 'corporations')

        response = await get_corp_statistics(id)
        await ctx.send(response)
    except Exception as e:
        await ctx.send("Could not use arguments.")


async def setup(bot):
    bot.add_command(corp)
