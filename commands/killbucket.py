from commands.killbucket_text_generator import judgment_phrase_generator, start_phrase_generator, help_text
from commands.killbucket_statistics import gather_buckets, make_plot
from utils import lookup
import discord
import datetime

help_message = "\n".join([
    "Usage:",
    "!killbucket",
    "<character_name>|<character_id> |",
    "-c|--corporation <corporation_name>|<corporation_id>",
    "-a|--alliance <alliance_name>|<alliance_id>",
    "[-d|--days <days_to_querry> | --alltime]"
])


async def command_killbucket(arguments, message):
    if "help" in arguments:
        await message.channel.send(help_message)
        return

    try:
        # Config
        character_days = 180
        corporation_days = 30
        alliance_days = 14

        if "help" in arguments or "h" in arguments:
            await message.channel.send(help_text(character_days, corporation_days, alliance_days))

        if "alliance" in arguments or "a" in arguments:
            name = " ".join(arguments["a"] if "a" in arguments else arguments["alliance"])
            id = lookup(name, 'alliances')
            aggregate = id
            querry = "allianceID"
            group = True
            days = alliance_days

        elif "corporation" in arguments or "c" in arguments:
            name = " ".join(arguments["c"] if "c" in arguments else arguments["corporation"])
            id = lookup(name, 'corporations')
            group = True
            aggregate = id
            querry = "corporationID"
            days = corporation_days

        else:
            name = " ".join(arguments[""])
            id = lookup(name, 'characters')
            group = False
            aggregate = None
            querry = "characterID"
            days = character_days

        if "days" in arguments:
            days = int(arguments["days"][0])
        elif "d" in arguments:
            days = int(arguments["d"][0])

        until = datetime.datetime.utcnow() - datetime.timedelta(days=days)

        if "alltime" in arguments:
            until = datetime.datetime(2003, 5, 6, 0, 0)  # Eve release date
            days = (datetime.datetime.utcnow() - until).days

        await message.channel.send(start_phrase_generator(group) + '\n This might take a minute...')

        kill_buckets = await gather_buckets(
            f"https://zkillboard.com/api/kills/{querry}/{id}/kills/",
            until,
            aggregate=aggregate
        )

        await make_plot(
            kill_buckets,
            f"Involved Pilots per KM for {name} in the past {days} days{' (per individual pilot)' if group else ''}"
        )

        await message.channel.send(
            file=discord.File('plot.png'),
            content=judgment_phrase_generator(name, id, kill_buckets, days, group)
        )
    except Exception as e:
        await message.channel.send("Could not find data for that. " + help_message)


async def command_linkkb(arguments, message):
    try:
        await message.channel.send(f"https://zkillboard.com/character/{lookup(' '.join(arguments['']), 'characters')}/")
    except ValueError:
        await message.channel.send('I\'m not sure who that is')
