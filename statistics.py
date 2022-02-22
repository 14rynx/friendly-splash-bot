import json
import asyncio
import aiohttp
import matplotlib.pyplot as plt
import ssl
import certifi
from datetime import datetime, timedelta

plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color'] = color
plt.rcParams['axes.labelcolor'] = color
plt.rcParams['xtick.color'] = color
plt.rcParams['ytick.color'] = color
plt.rc('axes', edgecolor=color)


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
        while len(kill_overflow) == 0 and page < 100:
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


async def make_plot(url, days, title, shift_for_char=False):
    # Generate Statistics
    killbuckets = await gather_kills(url, datetime.utcnow() - timedelta(days=days))

    if shift_for_char:
        killbuckets['five'] *= 3.5
        killbuckets['ten'] *= 8
        killbuckets['fifteen'] *= 13
        killbuckets['twenty'] *= 18
        killbuckets['thirty'] *= 25.5
        killbuckets['forty'] *= 35.5
        killbuckets['fifty'] *= 45.5
        killbuckets['blob'] *= 75

    # Make plot
    plt.bar(killbuckets.keys(), killbuckets.values(), align='center', alpha=0.5, color=color)
    plt.ylabel('Number of Kills')
    plt.title(title, color=color)
    fig1 = plt.gcf()

    # Save Plot
    fig1.savefig(fname='plot.png', transparent=True)
    plt.clf()

    return killbuckets
