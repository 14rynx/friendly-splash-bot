import requests
import json
import asyncio
import aiohttp
import matplotlib.pyplot as plt
import discord
import random
import yfinance as yf
import ssl
import certifi
import os
from datetime import datetime, timedelta

plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color'] = color
plt.rcParams['axes.labelcolor'] = color
plt.rcParams['xtick.color'] = color
plt.rcParams['ytick.color'] = color
plt.rc('axes', edgecolor=color)
from keep_alive import keep_alive
from text_generator import phrase_generator, start_generator, help_text

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
client = discord.Client()

def stonks(ticker):
    try:
        tickerData = yf.Ticker(ticker)
        tickerDf = tickerData.history(period='1d')
        return round(tickerDf['Close'][0], 4)
    except:
        return 'error'


def killboard():
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


def char_id_lookup(char_name):
    resp = requests.get(f"https://esi.evetech.net/legacy/search/?categories=character&datasource=tranquility&language=en-us&search={char_name}&strict=true")
    return resp.json()['character'][0]


def get_buckets(zkill_id):
    # dictionary for how many pilots involved in killmails
    pilots_involved = {
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
    char_id = zkill_id

    try:
        kills = asyncio.run(gather_kills(f"https://zkillboard.com/api/kills/characterID/{char_id}/kills/", datetime.utcnow() - timedelta(days=90)))

        for kill in kills:
            if "attackers" in kill:
                pilots = len(kill["attackers"])
                if pilots == 1:
                    pilots_involved["solo"] += 1
                elif pilots < 5:
                    pilots_involved["five"] += 1
                elif pilots < 10:
                    pilots_involved["ten"] += 1
                elif pilots < 15:
                    pilots_involved["fifteen"] += 1
                elif pilots < 20:
                    pilots_involved["twenty"] += 1
                elif pilots < 30:
                    pilots_involved["thirty"] += 1
                elif pilots < 40:
                    pilots_involved["forty"] += 1
                elif pilots < 50:
                    pilots_involved["fifty"] += 1
                elif pilots >= 50:
                    pilots_involved["blob"] += 1

        return pilots_involved
    except:
        return 'error'  # if literally anything goes wrong


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
        print(f'someone requested info on {message.content[8:]}')
        await message.channel.send(f"{message.content[8:]} Current Price= {str(stonks(message.content[8:].strip()))}")

    elif message.content.startswith('!linkkb'):
        try:
            await message.channel.send(f"https://zkillboard.com/character/{char_id_lookup(message.content[8:])}/")
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

    elif message.content.startswith('!killbucket'):
        if message.content == '!killbucket help':
            await message.channel.send(help_text())
        else:
            await message.channel.send(start_generator() + '\n This might take a minute...')
            kill_id = message.content[12:]
            try:
                int_char_id = int(kill_id)
            except ValueError:
                try:
                    int_char_id = int(char_id_lookup(kill_id))
                except:
                    await message.channel.send('I don\'t know who you\'re talking about')
                    return

                kills = get_buckets(int_char_id)  # assumes !killbucket_zkillid
                if kills == 'error':
                    await message.channel.send('Something went wrong, probably invalid zkill ID')
                else:
                    # Logging
                    with open('pilots.txt', "a") as f:
                        print(str(int_char_id) + "\n", file=f)

                    # Make plot
                    plt.bar(kills.keys(), kills.values(), align='center', alpha=0.5, color=color)
                    plt.ylabel('Number of Kills')
                    plt.title(f'Involved Pilots per KM for zkillID: {kill_id}', color=color)
                    fig1 = plt.gcf()
                    fig1.savefig(fname='plot.png', transparent=True)
                    plt.clf()

                    # Send message
                    await message.channel.send(file=discord.File('plot.png'), content=phrase_generator(kill_id, kills))


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


# Function to get all kills from a zkb link
async def gather_kills(zkill_url, end_date):
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    data = []
    over = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        page = 1
        while len(over) == 0 and page < 10:
            async with session.get(f"{zkill_url}page/{page}/") as response:
                try:
                    kills = await response.json(content_type=None)
                except json.decoder.JSONDecodeError:
                    continue  # We just try again

                if type(kills) is dict:
                    tasks = [get_kill(session, *kill, end_date, data, over) for kill in kills.items()]
                else:
                    tasks = [get_kill(session, kill["killmail_id"], kill["zkb"]["hash"], end_date, data, over) for kill in kills]
                await asyncio.gather(*tasks)
                page += 1

    return data


keep_alive()
client.run(os.getenv('TOKEN'))
