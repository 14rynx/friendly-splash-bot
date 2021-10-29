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
from text_generator import phrase_generator, start_generator, help_text

# Config
days = 180

plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color'] = color
plt.rcParams['axes.labelcolor'] = color
plt.rcParams['xtick.color'] = color
plt.rcParams['ytick.color'] = color
plt.rc('axes', edgecolor=color)

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
client = discord.Client()


def stonks(ticker):
    ticker_data = yf.Ticker(ticker)
    ticker_df = ticker_data.history(period='1d')
    return round(ticker_df['Close'][0], 4)


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
    resp = requests.get(f"https://esi.evetech.net/legacy/search/?categories=character&datasource=tranquility&"
                        f"language=en-us&search={char_name}&strict=true")
    return resp.json()['character'][0]


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

    elif message.content == '!killbucket help':
        await message.channel.send(help_text(days))

    elif message.content.startswith('!killbucket'):
        await message.channel.send(start_generator() + '\n This might take a minute...')
        character = message.content[12:]
        try:
            character_id = int(character)
        except ValueError:
            try:
                character_id = int(char_id_lookup(character))
            except:
                await message.channel.send('I don\'t know who you\'re talking about')
                return

        killbuckets = await gather_kills(
            f"https://zkillboard.com/api/kills/characterID/{character_id}/kills/",
            datetime.utcnow() - timedelta(days=days)
        )

        # Logging
        with open('pilots.txt', "a") as f:
            print(str(character_id), file=f)

        # Make plot
        plt.bar(killbuckets.keys(), killbuckets.values(), align='center', alpha=0.5, color=color)
        plt.ylabel('Number of Kills')
        plt.title(f'Involved Pilots per KM for zkillID: {character}', color=color)
        fig1 = plt.gcf()
        fig1.savefig(fname='plot.png', transparent=True)
        plt.clf()

        # Send message
        await message.channel.send(file=discord.File('plot.png'), content=phrase_generator(character, killbuckets, days))


async def get_kill(session, kill_id, kill_hash, start, buckets, over):
    async with session.get(f"https://esi.evetech.net/latest/killmails/{kill_id}/{kill_hash}/?datasource=tranquility") as resp:
        try:
            kill = await resp.json(content_type=None)
            if "killmail_time" in kill:
                time = datetime.strptime(kill['killmail_time'], '%Y-%m-%dT%H:%M:%SZ')
                if start < time:
                    if "attackers" in kill:
                        pilots = len(kill["attackers"])
                        if pilots == 1:
                            buckets["solo"] += 1
                        elif pilots < 5:
                            buckets["five"] += 1
                        elif pilots < 10:
                            buckets["ten"] += 1
                        elif pilots < 15:
                            buckets["fifteen"] += 1
                        elif pilots < 20:
                            buckets["twenty"] += 1
                        elif pilots < 30:
                            buckets["thirty"] += 1
                        elif pilots < 40:
                            buckets["forty"] += 1
                        elif pilots < 50:
                            buckets["fifty"] += 1
                        elif pilots >= 50:
                            buckets["blob"] += 1
                else:
                    over.append(kill)
        except json.decoder.JSONDecodeError:
            await get_kill(session, kill_id, kill_hash, start, buckets, over)


# Function to get all kills from a zkb link
async def gather_kills(zkill_url, end_date):
    ssl_context = ssl.create_default_context(cafile=certifi.where())

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
    kill_overflow = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        page = 1
        while len(kill_overflow) == 0 and page < 10:
            async with session.get(f"{zkill_url}page/{page}/") as response:
                try:
                    ids_hashes_response = await response.json(content_type=None)
                except json.decoder.JSONDecodeError:
                    continue  # We just try again

                if type(ids_hashes_response) is dict:
                    tasks = [get_kill(session, *id_hash, end_date, buckets, kill_overflow) for id_hash in ids_hashes_response.items()]
                else:
                    tasks = [get_kill(session, zkb_json["killmail_id"], zkb_json["zkb"]["hash"], end_date, buckets, kill_overflow) for zkb_json in ids_hashes_response]
                await asyncio.gather(*tasks)
                page += 1

    return buckets

client.run(os.getenv('TOKEN'))
