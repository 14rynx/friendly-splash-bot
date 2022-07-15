from datetime import datetime
import asyncio
import aiohttp
import ssl
import certifi
import json


# Functions to get a kill from esi
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


# Function to get all kills from a zkb link in timeframe
async def gather_kills(zkill_url, start):
    # Workaround for aiohttp not coming with certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    data = []
    over = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        page = 1
        while len(over) == 0 and page < 100:
            async with session.get(f"{zkill_url}page/{page}/") as response:
                try:
                    kills = await response.json(content_type=None)
                except json.decoder.JSONDecodeError:
                    continue  # We just try again

                if type(kills) is dict:
                    tasks = [get_kill(session, *kill, start, data, over) for kill in kills.items()]
                else:
                    tasks = [get_kill(session, kill["killmail_id"], kill["zkb"]["hash"], start, data, over) for kill in
                             kills]

                await asyncio.gather(*tasks)
                page += 1
    return data
