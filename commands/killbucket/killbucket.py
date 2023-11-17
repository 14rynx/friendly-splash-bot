import datetime

import discord
from discord.ext import commands

from commands.killbucket.statistics import gather_buckets, make_plot
from commands.killbucket.text_generator import judgment_phrase_generator, start_phrase_generator, help_text
from utils import lookup, unix_style_arg_parser


@commands.command()
async def killbucket(ctx, *args):
    """
    !killbucket <character_name>|<character_id> |
        -c|--corporation <corporation_name>|<corporation_id>
        -a|--alliance <alliance_name>|<alliance_id>
    [-d|--days <days_to_querry> | --alltime]
    """
    arguments = unix_style_arg_parser(args)

    try:
        # Config
        character_days = 180
        corporation_days = 30
        alliance_days = 14

        if "help" in arguments or "h" in arguments:
            await ctx.send(help_text(character_days, corporation_days, alliance_days))

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

        await ctx.send(start_phrase_generator(group) + '\n This might take a minute...')

        kill_buckets = await gather_buckets(
            f"https://zkillboard.com/api/kills/{querry}/{id}/kills/",
            until,
            aggregate=aggregate
        )

        await make_plot(
            kill_buckets,
            f"Involved Pilots per KM for {name} in the past {days} days{' (per individual pilot)' if group else ''}"
        )

        await ctx.send(
            file=discord.File('plot.png'),
            content=judgment_phrase_generator(name, id, kill_buckets, days, group)
        )
    except Exception as e:
        await ctx.send("Could not find data for that.")


@commands.command()
async def linkkb(ctx, *args):
    """
    !linkkb <character_name>|<character_id>
    """
    try:
        await ctx.send(f"https://zkillboard.com/character/{lookup(' '.join(*args), 'characters')}/")
    except ValueError:
        await ctx.send('I\'m not sure who that is')


async def setup(bot):
    bot.add_command(killbucket)
    bot.add_command(linkkb)
