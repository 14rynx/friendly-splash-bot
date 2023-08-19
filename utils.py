import asyncio
import json
import ssl
from datetime import datetime

import aiohttp
import certifi
import requests


def lookup(string, return_type):
    """Tries to find an ID related to the input.

    Parameters
    ----------
    string : str
        The character / corporation / alliance name
    return_type : str
        what kind of id should be tried to match
        can be characters, corporations and alliances

    Raises
    ------
    ValueError, JSONDecodeError ...
    """
    try:
        return int(string)
    except ValueError:
        try:
            response = requests.post('https://esi.evetech.net/latest/universe/ids/?datasource=tranquility&language=en',
                                     json=[string])
            return max(response.json()[return_type], key=lambda x: x["id"])["id"]
        except requests.exceptions.RequestException:
            raise ValueError


def isk(number):
    """Takes a number and converts it into an ingame-like ISK format string.

    Parameters
    ----------
    number : int / float
        amount of Interstellar Kredits to display
    """

    return format(number, ",.0f").replace(',', "'") + " ISK"


def convert(number_string):
    """Takes a number-string and converts it into a number, taking common abbreviations.

    Parameters
    ----------
    number_string : str
        something like 1b, 15m 10kk
    """
    exponent = 3 * number_string.lower().count("k") + 6 * number_string.lower().count(
        "m") + 9 * number_string.lower().count("b")
    number = float(number_string.lower().replace("k", "").replace("m", "").replace("b", ""))
    return number * 10 ** exponent


# Functions to get a kill from esi
async def get_kill(session, id, hash, start, data, over):
    """Gets a single kill from ESI and decides if it is in a valid date range

    Parameters
    ----------
    session : asyncio client session
        amount of Interstellar Kredits to display
    id : int
        Kill ID.
    id : str
        Kill Hash for authentification with ESI
    start : datetime
        The oldest allowed timestamp for a valid killmail.
    data : list
        All valid killmails get added to this.
    over : list
        All invalid killmails get added to this.
    """
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
    """Gets all killmails before after a certain timestamp

    Parameters
    ----------
    zkill_url : str
        The zkillboard.com url to fetch kills from.
    start : datetime
        The oldest allowed timestamp for a valid killmail.
    """
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


class RelationalSorter:
    @staticmethod
    def interpolate(x1, y1, x2, y2, x_target):
        assert (x1 <= x_target <= x2)
        dx = x2 - x1
        rx = x_target - x1
        dy = y2 - y1

        if dx != 0:
            return y1 + dy / dx * rx
        else:
            return y1

    def __init__(self, all_points):
        self.best = list(sorted(all_points, key=lambda x: x[0]))

        old_len = 0
        while (old_len != len(self.best)):
            old_len = len(self.best)

            interpolated_prices = [0] + [
                RelationalSorter.interpolate(*self.best[i - 1], *self.best[i + 1], self.best[i][0]) for i in
                range(1, len(self.best) - 1)] + [0]
            self.best = [i for i, j in zip(self.best, interpolated_prices) if i[1] > j]

    def __call__(self, point):
        try:
            index = next(i for i, val in enumerate(self.best) if val[0] > point[0])
        except StopIteration:
            return 1.0
        else:
            interpolated_bonus = RelationalSorter.interpolate(*self.best[index - 1], *self.best[index], point[0])
            return point[1] / interpolated_bonus


async def get_url(url, session, other_data=None):
    """returns data from a single url, appends 'other_data' """
    if other_data:
        async with session.get(url) as response:
            try:
                return await response.json(content_type=None), other_data
            except json.JSONDecodeError:
                return [], other_data
    else:
        async with session.get(url) as response:
            try:
                return await response.json(content_type=None)
            except json.JSONDecodeError:
                return []


async def get_urls(urls, session, other_datas=None):
    """returns data from a set of urls as they complete, and correctly matches 'other_datas' to it"""
    if other_datas:
        tasks = [get_url(url, session, other_data) for url, other_data in zip(urls, other_datas)]
        for task in asyncio.as_completed(tasks):
            yield await task
    else:
        tasks = [get_url(url, session) for url in urls]
        for task in asyncio.as_completed(tasks):
            yield await task


async def get_item_name(type_id, session):
    async with session.get(f"https://esi.evetech.net/latest/universe/types/{type_id}/") as response:
        if response.status == 200:
            return (await response.json(content_type=None))["name"]
        return f"Type ID: {type_id}"


async def get_item_price(type_id, session):
    async with session.get(f"https://market.fuzzwork.co.uk/aggregates/?region=10000002&types={type_id}") as response:
        return float((await response.json())[str(type_id)]["sell"]["min"])
