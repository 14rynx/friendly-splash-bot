import requests
import json
import asyncio
import discord
import random
import yfinance as yf
from text_generator import character_judgment_phrase_generator, character_start_phrase_generator, help_text, group_judgment_phrase_generator, group_start_phrase_generator
from statistics import make_plot
import os

# Config
character_days = 180
corporation_days = 30
alliance_days = 14


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
client = discord.Client()


def killboard():
    """returns the current leaderboard as str"""

    # open the current leaderboard json
    with open('json-weekly.txt', 'r') as infile:
        leaderboard = json.load(infile)
    string = ''
    # build the message

    for bucket in leaderboard.keys():
        string += f'**{bucket.capitalize()}:**\n'
        for place, data in leaderboard[bucket].items():
            string += f':{place}_place: {data["pilotname"]} - {data["count"]}\n'
        string += '\n'
    return string


def lookup(string, type):
    """Tries to find an ID related to the input

    Parameters
    ----------
    string : str
        The sound the animal makes (default is None)

    type : str
        what kind of id should be tried to match
        can be character, corporation and alliance

    Raises
    ------
    ValueError
        If no suitable conversion can be found
    """

    try:
        id = int(string)
    except ValueError:
        try:
            id = int(requests.get(f"https://esi.evetech.net/legacy/search/?categories={type}&datasource=tranquility&"
                        f"language=en-us&search={string}&strict=true").json()[type][0])
        except:
            raise ValueError
    return id


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:  # It is our own message
        return

    elif message.content == '!bucketboard':
        await message.channel.send(killboard())

    elif message.content.startswith('!stonks'):
        ticker_df = yf.Ticker(message.content[8:]).history(period='1d')
        await message.channel.send(f"{message.content[8:]} Current Price= {round(ticker_df['Close'][0], 4)}")

    elif message.content.startswith('!linkkb'):
        try:
            await message.channel.send(f"https://zkillboard.com/character/{lookup(message.content[8:], 'character')}/")
        except:
            await message.channel.send('I\'m not sure who that is')

    elif message.content.startswith('!teams'):
        pilots = message.content[7:].split(',')
        team_size = len(pilots) // 2
        random.shuffle(pilots)
        await message.channel.send("\n".join(
            [f"Referee: {pilots[-1]}" if len(pilots) % 2 else ""]
            + ["1:"] + pilots[:team_size]
            + ["2:"] + pilots[team_size: 2 * team_size]
        ))

    elif message.content == '!killbucket --help' or message.content == '!killbucket -h' or  message.content == '!help':
        await message.channel.send(help_text(character_days, corporation_days, alliance_days))

    elif message.content.startswith('!killbucket --alliance') or message.content.startswith('!killbucket -a'):
        await message.channel.send(group_start_phrase_generator() + '\n This might take a minute...')

        try:
            # Input
            if message.content.startswith('!killbucket -a'):
                alliance_input = message.content[15:]
            else:
                alliance_input = message.content[23:]
            alliance_id = lookup(alliance_input, "alliance")

            # Statistics
            buckets = await make_plot(
                f"https://zkillboard.com/api/kills/allianceID/{alliance_id}/kills/",
                alliance_days,
                f"Involved Pilots per KM for: {alliance_input} \n Adjusted for Average Pilot",
                shift_for_char=True
            )

            # Logging
            with open('alliances.txt', "a") as f:
                print(str(alliance_id), file=f)

            # Output
            await message.channel.send(file=discord.File('plot.png'),
                                       content=group_judgment_phrase_generator(alliance_input, buckets, alliance_days))

        except ValueError:
            await message.channel.send('I\'m not sure who those guys are')

    elif message.content.startswith('!killbucket --corporation') or message.content.startswith('!killbucket -c'):
        await message.channel.send(group_start_phrase_generator() + '\n This might take a minute...')

        try:
            #Input
            if message.content.startswith('!killbucket -c'):
                corp_input = message.content[15:]
            else:
                corp_input = message.content[26:]
            corporation_id = lookup(corp_input, "corporation")

            # Statistics
            buckets = await make_plot(
                f"https://zkillboard.com/api/kills/corporationID/{corporation_id}/kills/",
                corporation_days,
                f"Involved Pilots per KM for: {corp_input} \n Adjusted for Average Pilot",
                shift_for_char=True
            )

            # Logging
            with open('corps.txt', "a") as f:
                print(str(corporation_id), file=f)

            # Output
            await message.channel.send(file=discord.File('plot.png'),
                                       content=group_judgment_phrase_generator(corp_input, buckets, corporation_days))

        except ValueError:
            await message.channel.send('I\'m not sure who those guys are')

    elif message.content.startswith('!killbucket'):
        await message.channel.send(character_start_phrase_generator() + '\n This might take a minute...')

        try:
            #Input
            char_input = message.content[12:]
            character_id = lookup(char_input, "character")

            # Statistics
            buckets = await make_plot(
                f"https://zkillboard.com/api/kills/characterID/{character_id}/kills/",
                character_days,
                f"Involved Pilots per KM for: {char_input}"
            )

            # Logging
            with open('chars.txt', "a") as f:
                print(str(character_id), file=f)

            # Output
            await message.channel.send(file=discord.File('plot.png'),
                                       content=character_judgment_phrase_generator(character_id, char_input, buckets, character_days))

        except ValueError:
            await message.channel.send('I\'m not sure who that is')

client.run(os.getenv('TOKEN'))
