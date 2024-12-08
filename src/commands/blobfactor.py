from datetime import datetime, timedelta, UTC

from discord.ext import commands

from network import id_lookup, fetch_kill_until
from utils import unix_style_arg_parser, command_error_handler


@commands.command()
@command_error_handler
async def blobfactor(ctx, *args):
    """
    !blobfactor <character_name> | <character_id> |
            -c|--corporation <corporation_name>|<corporation_id>
            -a|--alliance <alliance_name>|<alliance_id>
        [-d|--days <days_to_querry> | --alltime]
    """
    arguments = unix_style_arg_parser(args)

    # Config
    character_days = 180
    corporation_days = 30
    alliance_days = 14

    if "alliance" in arguments or "a" in arguments:
        name = " ".join(arguments["a"] if "a" in arguments else arguments["alliance"])
        id = id_lookup(name, 'alliances')
        url = f"https://zkillboard.com/api/kills/allianceID/{id}/kills/"
        days = alliance_days
    elif "corporation" in arguments or "c" in arguments:
        name = " ".join(arguments["c"] if "c" in arguments else arguments["corporation"])
        id = id_lookup(name, 'corporations')
        url = f"https://zkillboard.com/api/kills/corporationID/{id}/kills/"
        days = corporation_days
    else:
        name = " ".join(arguments[""])
        id = id_lookup(name, 'characters')
        url = f"https://zkillboard.com/api/kills/characterID/{id}/kills/"
        days = character_days

    if "days" in arguments:
        days = int(arguments["days"][0])
    elif "d" in arguments:
        days = int(arguments["d"][0])

    until = datetime.now(UTC) - timedelta(days=days)

    if "alltime" in arguments:
        until = datetime(2003, 5, 6, 0, 0)  # Eve release date
        days = (datetime.now(UTC) - until).days

    friendlies = []
    kills = []
    async for kill in await fetch_kill_until(f"{url}/kills/", until):
        kills.append(kill)
        friendlies.extend(kill['attackers'])

    enemies = []
    losses = []
    async for loss in await fetch_kill_until(f"{url}/losses/", until):
        losses.append(loss)
        enemies.extend(loss['attackers'])

    if "thirdparty" in arguments and arguments["thirdparty"] == ["no"]:  # WTF is this!?
        friendlies = [f for f in friendlies if "corporation_id" in f and f["corporation_id"] == 98633005]
        enemies = [e for e in enemies if "corporation_id" in e and e["corporation_id"] != 98633005]

    await ctx.send(
        f"**{name}'s last {days} days ** (analyzed {len(kills)} kills and {len(losses)} losses) \n"
        f"Average Pilots on kill: {len(friendlies) / len(kills) :.2f}\n"
        f"Average Enemies on loss: {len(enemies) / len(losses) :.2f}\n"
        f"Blob Factor: {len(friendlies) / len(kills) * len(losses) / len(enemies) :.2f}"
    )


async def setup(bot):
    bot.add_command(blobfactor)
