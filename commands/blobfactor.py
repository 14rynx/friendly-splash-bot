from datetime import datetime, timedelta
from utils import lookup, gather_kills


help_message = "\n".join([
    "Usage:",
    "!blobfactor",
    "<character_name>|<character_id> |",
    "-c|--corporation <corporation_name>|<corporation_id>",
    "-a|--alliance <alliance_name>|<alliance_id>",
    "[-d|--days <days_to_querry> | --alltime]"
])


async def command_blobfactor(arguments, message):

    if "help" in arguments:
        await message.channel.send(help_message)
        return

    try:
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

        until = datetime.utcnow() - timedelta(days=days)

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
    except Exception as e:
        await message.channel.send("Could not find data for that. " + help_message)
