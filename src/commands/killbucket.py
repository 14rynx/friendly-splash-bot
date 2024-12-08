import datetime
import random

import discord
import matplotlib.pyplot as plt
from discord.ext import commands

from network import fetch_kill_until, id_lookup
from utils import unix_style_arg_parser, command_error_handler


def start_phrase_generator(group):
    if not group:
        return random.choice([
            'You are probably a filthy blobber, we\'ll see.',
            'Small gang best gang.', 'Backpacks dont\'t count.',
            'Strix Ryden #2!',
            'I miss offgrid links.',
            'You and 4 alts is BARELY solo.',
            'Damn Pyfa warriors'
        ])
    else:
        return random.choice([
            'You are probably all filthy blobbers, we\'ll see.',
            'Small gang best gang.', 'Backpacks dont\'t count.',
            'Strix Ryden #2!',
            'We miss offgrid links',
            '9 dudes with 5 alts is barely less than ten',
            'Pyfa Warrior Alliance Please Ignore'
        ])


def character_solo_generator(name):
    return f' **{name} - You don\'t have many friends do you?**'


def character_smallgang_generator(name):
    return random.choice([
        f'Did you wear your mouse out clicking in space?\n**{name} - You\'re an elitist nano prick**',
        f'What\'s an anchor and why do I need one?\n**{name} - You\'re an elitist nano prick**',
        f'We don\'t need no stinking FC.\n**{name} - You\'re an elitist nano prick**',
        f'Kitey nano bitch.\n**{name} - You\'re an elitist nano prick**',
        f'How many backpacks do you lose?\n**{name} - You\'re an elitist nano prick**',
        f'Wormholer BTW\n**{name} - You\'re an elitist nano prick**',
        f'Don\'t forget your HG snake pod\n**{name} - You\'re an elitist nano prick**',
        f'You\'d be even more elite with some purple on that ship.\n**{name} - You\'re an elitist nano prick**'
    ])


def character_blobber_generator(name):
    return random.choice([
        f'FC when do I hit F1?\n**{name} - You\'re a blobber**',
        f'FC can I bring my drake?\n**{name} - You\'re a blobber**',
        f'Who is the anchor?\n**{name} - You\'re a blobber**',
        f'How\'s that blue donut treating you?\n**{name} - You\'re a blobber**',
        f'You must be part of some nullsec alliance.\n**{name} - You\'re a blobber**',
        f'You\'ve never heard of a nanofiber have you.\n**{name} - You\'re a blobber**',
        f'My sky marshall said stay docked.\n**{name} - You\'re a blobber**',
        f'I bet you\'ve got the record in your alliance for station spin counter though! \n**{name} - You\'re a blobber**'
    ])


def character_midgang_generator(name):
    return random.choice([
        f'You should probably listen to <10 instead of TiS.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Well you tried, but you should try harder.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Guess you must be a response fleet whore\n**{name} - Almost...still not cool enough to be elitist**',
        f'Probably an input broadcaster.\n**{name} - Almost...still not cool enough to be elitist**',
        f'So you, your five friends each with 3 alts. Got it.\n**{name} - Almost...still not cool enough to be elitist**'
    ])


def character_activity_generator(name, kill_buckets, requirement):
    if sum(kill_buckets.values()) < requirement:
        return f"\n And you don\'t undock much, do you?"
    return ""


def group_solo_generator(name):
    return f' **{name} - Duh, do you all play for your own?**'


def group_smallgang_generator(name):
    return random.choice([
        f'Does your group do Mouse SRP?\n**{name} - You\'re all elitist nano pricks**',
        f'What\'s an anchor and why do I need one?\n**{name} - You\'re all elitist nano pricks**',
        f'We don\'t need no stinking FC.\n**{name} - You\'re all elitist nano pricks**',
        f'This is a battlefield, not a drag race!\n**{name} - You\'re all elitist nano pricks**',
        f'How many backpacks do you lose?\n**{name} - You\'re all elitist nano pricks**',
        f'Keepstar anchored - Vonhole invited\n**{name} - You\'re all elitist nano pricks**',
        f'Don\'t forget your HG snake pods\n**{name} - You\'re all elitist nano pricks**',
        f'So many 100mns, must be a Tuskers copy\n**{name} - You\'re all elitist nano pricks**'
    ])


def group_blobber_generator(name):
    return random.choice([
        f'FC when do I hit F1?\n**{name} - Don\'t forget your 5 Monitors**',
        f'FC can I bring my drake?\n**{name} - You\'re all blobbers**',
        f'Who is the anchor?\n**{name} - Blobbers, Blobbers, blobbers ... and a few more**',
        f'How\'s that blue donut treating you?\n**{name} - - You\'re all blobbers**',
        f'You must be some "feared" nullsec group.\n**{name} - You\'re all blobbers**',
        f'Theorycrafting is only for FC\'s right? \n**{name} - - You\'re all blobbers**',
        f'Sky marshall said stay docked.\n**{name} - - You\'re all blobbers**',
        f'At least you have a strong presence on reddit! \n**{name}- You\'re all blobbers**'
    ])


def group_midgang_generator(name):
    return random.choice([
        f'You should probably listen to <10 instead of TiS.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Well you guys tried, but you should try harder.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Enough dudes on grid so that they surely all are tackled? \n**{name} - Not quite enough to be **',
        f'Protean Concept would be proud with so many OP ships on a Grid\n**{name} - Go from C4 to C2 and you are worth something **',
        f'Probably an input broadcaster.\n**{name} - Almost...still not cool enough to be elitist**',
        f'So you, your five friends each with 3 alts. Got it.\n**{name} - Almost...still not cool enough to be elitist**'
    ])


def judgment_phrase_generator(name, id, kills, days, group):
    if not group:
        if sum(kills.values()) < days / 4:
            return f"{name} - you are a true discord warrior!"

        small_gang = kills['solo'] + kills['five'] + kills['ten']
        blob_gang = kills['forty'] + kills['fifty'] + kills['blob']
        mid_gang = kills['fifteen'] + kills['twenty'] + kills['thirty']

        if id == 2113113522:
            return "<@242164531151765505> someone is looking for you"

        if max(kills, key=lambda key: kills[key]) == 'solo':
            return character_solo_generator(name) + character_activity_generator(name, kills,
                                                                                 days / 2)  # One Kill every other day
        elif small_gang < blob_gang and mid_gang < blob_gang:
            return character_blobber_generator(name) + character_activity_generator(name, kills,
                                                                                    2 * days)  # Two Kills a day
        elif mid_gang > small_gang:
            return character_midgang_generator(name) + character_activity_generator(name, kills,
                                                                                    2 * days)  # Two Kills a day
        else:
            return character_smallgang_generator(name) + character_activity_generator(name, kills,
                                                                                      days)  # One Kill a day
    else:
        if sum(kills.values()) < days / 2:
            return f"{name} - you guys are true discord warriors!"

        small_gang = kills['solo'] + kills['five'] + kills['ten']
        blob_gang = kills['forty'] + kills['fifty'] + kills['blob']
        mid_gang = kills['fifteen'] + kills['twenty'] + kills['thirty']

        if kills['solo'] > max(small_gang, mid_gang, blob_gang):
            return group_solo_generator(name)
        elif small_gang < blob_gang and mid_gang < blob_gang:
            return group_blobber_generator(name)
        elif mid_gang > small_gang:
            return group_midgang_generator(name)
        else:
            return group_smallgang_generator(name)


# Function to get all kills from a zkb link
async def gather_buckets(zkill_url, end_date, aggregate):
    buckets = {
        "solo": 0,
        "five": 0,
        "ten": 0,
        "fifteen": 0,
        "twenty": 0,
        "thirty": 0,
        "forty": 0,
        "fifty": 0,
        "blob": 0,
    }

    async for kill in fetch_kill_until(zkill_url, start=end_date):
        pilots = len(kill["attackers"])
        friendlies = max(1, len([a for a in kill["attackers"] if
                                 "corporation_id" in a and a["corporation_id"] == aggregate or "alliance_id" in a and a[
                                     "alliance_id"] == aggregate]))
        if pilots == 1:
            buckets["solo"] += friendlies
        elif pilots < 5:
            buckets["five"] += friendlies
        elif pilots < 10:
            buckets["ten"] += friendlies
        elif pilots < 15:
            buckets["fifteen"] += friendlies
        elif pilots < 20:
            buckets["twenty"] += friendlies
        elif pilots < 30:
            buckets["thirty"] += friendlies
        elif pilots < 40:
            buckets["forty"] += friendlies
        elif pilots < 50:
            buckets["fifty"] += friendlies
        elif pilots >= 50:
            buckets["blob"] += friendlies

    return buckets


async def make_plot(kill_buckets, title):
    plt.bar(kill_buckets.keys(), kill_buckets.values(), align='center', alpha=0.5, color=color)
    plt.ylabel('Number of Kills')
    plt.title(title, color=color)
    fig1 = plt.gcf()

    fig1.savefig(fname='plot.png', transparent=True)
    plt.clf()


@commands.command()
@command_error_handler
async def killbucket(ctx, *args):
    """
    **Calculates buckets based on recent amount of Pilots involved in Killmails:**
    - For Characters         180 Days
    - For Corporations        30 Days
    - For Alliances           14 Days
    **And then assigns them into groups:**
    - For Small Gang     1 -   9 pilots
    - For Mid Gang     10 - 29 pilots
    - For Blob              30 +      pilots
     **Usage:**
    !killbucket
    <character_name>|<character_id> |
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
        id = await id_lookup(name, 'alliances')
        aggregate = id
        querry = "allianceID"
        group = True
        days = alliance_days

    elif "corporation" in arguments or "c" in arguments:
        name = " ".join(arguments["c"] if "c" in arguments else arguments["corporation"])
        id = await id_lookup(name, 'corporations')
        group = True
        aggregate = id
        querry = "corporationID"
        days = corporation_days

    else:
        name = " ".join(arguments[""])
        id = await id_lookup(name, 'characters')
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


@commands.command()
@command_error_handler
async def linkkb(ctx, *args):
    """
    !linkkb <character_name>|<character_id>
    """
    try:
        await ctx.send(f"https://zkillboard.com/character/{id_lookup(' '.join(*args), 'characters')}/")
    except ValueError:
        await ctx.send('I\'m not sure who that is')


plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color'] = color
plt.rcParams['axes.labelcolor'] = color
plt.rcParams['xtick.color'] = color
plt.rcParams['ytick.color'] = color
plt.rc('axes', edgecolor=color)


async def setup(bot):
    bot.add_command(killbucket)
    bot.add_command(linkkb)
