import json
import asyncio
import aiohttp
import matplotlib.pyplot as plt
import ssl
import certifi
from datetime import datetime, timedelta


async def put_in_bucket(session, kill_id, kill_hash, start, buckets, over, aggregate):
    async with session.get(f"https://esi.evetech.net/latest/killmails/{kill_id}/{kill_hash}/?datasource=tranquility") as resp:
        for tries in range(10):
            try:
                kill = await resp.json(content_type=None)
                time = datetime.strptime(kill['killmail_time'], '%Y-%m-%dT%H:%M:%SZ')
                if start < time:
                    pilots = len(kill["attackers"])
                    friendlies = max(1, len([a for a in kill["attackers"] if "corporation_id" in a and a["corporation_id"] == aggregate or "alliance_id" in a and a["alliance_id"] == aggregate]))
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
                else:
                    over.append(kill)
                break
            except (json.decoder.JSONDecodeError, KeyError):
                pass  # We try again up to 10 times


# Function to get all kills from a zkb link
async def gather_buckets(zkill_url, end_date, aggregate=None):
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
                    tasks = [put_in_bucket(session, *id_hash, end_date, buckets, kill_overflow, aggregate) for id_hash in ids_hashes_response.items()]
                else:
                    tasks = [put_in_bucket(session, zkb_json["killmail_id"], zkb_json["zkb"]["hash"], end_date, buckets, kill_overflow, aggregate) for zkb_json in ids_hashes_response]
                await asyncio.gather(*tasks)
                page += 1

    return buckets


plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color'] = color
plt.rcParams['axes.labelcolor'] = color
plt.rcParams['xtick.color'] = color
plt.rcParams['ytick.color'] = color
plt.rc('axes', edgecolor=color)


async def make_plot(kill_buckets, title):
    plt.bar(kill_buckets.keys(), kill_buckets.values(), align='center', alpha=0.5, color=color)
    plt.ylabel('Number of Kills')
    plt.title(title, color=color)
    fig1 = plt.gcf()

    fig1.savefig(fname='plot.png', transparent=True)
    plt.clf()
