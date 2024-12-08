import asyncio
import json
import logging
import random
import ssl
import string
import tarfile
from datetime import datetime
from io import BytesIO

import aiohttp
import certifi
from aiocache import cached

ssl_context = ssl.create_default_context(cafile=certifi.where())

# Configure the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Limit all traffic to 50 concurrent requests
esi_semaphore = asyncio.BoundedSemaphore(50)
error_limit = 100
error_delay = 0


def generate_headers(url):
    headers = {}

    user_agent = "Kibana-Statistics by Larynx Austrene <larynx.austrene@gmail.com> Python-Aiohttp"

    if "esi.evetech.net" in url:
        # Randomize user agent to avoid error caching
        headers['User-Agent'] = f"{user_agent}-{''.join(random.choices(string.ascii_letters + string.digits, k=8))}"
    else:
        headers['User-Agent'] = user_agent

    return headers


async def get(url) -> dict:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        # Wait for ESI errors to pass
        if "esi.evetech.net" in url:
            global error_limit, error_delay
            if error_limit < 1:
                await asyncio.sleep(error_delay)
                error_limit = 100

        async with esi_semaphore:

            # Retry logic with dynamic User-Agent for esi.evetech.net
            for attempt in range(20 if "esi.evetech.net" in url else 5):

                async with session.get(url, headers=generate_headers(url)) as response:

                    # Handle error limit headers for esi.evetech.net
                    if "esi.evetech.net" in url:
                        if (current_error_limit := int(
                                response.headers.get("X-Esi-Error-Limit-Remain", 100))) < error_limit:
                            error_limit = min(error_limit, current_error_limit)
                            error_delay = int(response.headers.get("X-Esi-Error-Limit-Reset", 0))

                    if response.status == 200:
                        try:
                            return await response.json(content_type=None)
                        except Exception as e:
                            logger.warning(f"Error {e} with ESI {response.status}: {await response.text()}")
                    elif 400 <= response.status <= 499:
                        raise ValueError(f"Url {url} got {response.status} with text {await response.text()}")

                    else:
                        logger.warning(f"Error with ESI {response.status}: {await response.text()}")

                    # Retry with backoff if esi.evetech.net
                    if "esi.evetech.net" in url:
                        if error_limit < 1:
                            await asyncio.sleep(error_delay)
                            error_limit = 100

                        await asyncio.sleep(0.5 * (attempt + 1))  # Linear backoff
                    else:
                        await asyncio.sleep(0.25 * (attempt + 1) ** 3)  # Cubic backoff

            raise ValueError(f"Could not fetch data from {url}!")


async def post(url, **kwargs) -> dict:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        # Wait for ESI error limit to pass
        if "esi.evetech.net" in url:
            global error_limit, error_delay
            if error_limit < 1:
                await asyncio.sleep(error_delay)
                error_limit = 100

        async with esi_semaphore:
            async with session.post(url, **kwargs) as response:

                # Fetch delay of lowest error limit
                if "esi.evetech.net" in url:
                    if (
                            current_error_limit := int(
                                response.headers.get("X-Esi-Error-Limit-Remain", 100))) < error_limit:
                        error_limit = current_error_limit
                        error_delay = int(response.headers.get("X-Esi-Error-Limit-Reset", 0))

                for attempt in range(10):
                    if response.status == 200:
                        try:
                            return await response.json(content_type=None)
                        except Exception as e:
                            logger.error(f"Error {e} with ESI {response.status}: {await response.text()}")
                    else:
                        logger.error(f"Error with ESI {response.status}: {await response.text()}")

                    if error_limit < 1:
                        await asyncio.sleep(error_delay)
                        error_limit = 100
                    await asyncio.sleep(0.25 * (attempt + 1) ** 3)  # Cubic Backoff on Error
                raise ValueError(f"Could not fetch data from ESI!")


@cached()
async def id_lookup(string, return_type):
    """
    Tries to find an ID related to the input.
    Parameters
    ----------
    string : str
        The name that should be converted into an ID
    return_type : str
        what kind of id should be tried to match
        Can be:
          "agents", "alliances", "characters", "constellations", "corporations", "factions",
          "inventory_types", "regions", "stations" or "systems"
    Raises
    ------
    ValueError:
        If the Value could not be converted.
    TimeoutError:
        If the EVE-Servers are not responding with a 200 status code.
    """
    try:
        return int(string)
    except ValueError:
        url = 'https://esi.evetech.net/latest/universe/ids/?datasource=tranquility&language=en'
        data = await post(url, json=[string])
        return max(data[return_type], key=lambda x: x["id"])["id"]


async def get_hash(kill_id):
    url = f"https://zkillboard.com/api/killID/{kill_id}/"
    return (await get(url))[0]['zkb']['hash']


async def get_kill(kill_id, kill_hash):
    url = f"https://esi.evetech.net/latest/killmails/{kill_id}/{kill_hash}/?datasource=tranquility"
    return await get(url)


async def gather_kills(kills):
    tasks = [get_kill(*kill) for kill in kills.items()]
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            yield result
        except ValueError:
            # Skip this one due to ESI Error
            continue


async def get_kill_page(url, page):
    page_url = f"{url}/page/{page}/"
    page_data = await get(page_url)

    # Extract data, which might be differently encoded depending on how zkill does it
    if type(page_data) is not dict:
        kills = {kill["killmail_id"]: kill["zkb"]["hash"] for kill in page_data}
    else:
        kills = page_data

    # Filter out wired kills that do not actually exist
    kills = {k: h for k, h in kills.items() if h != "CCP VERIFIED"}

    return kills


# Function to get all kills from a zkb link in timeframe
async def fetch_kill_until(url, start):
    """Gets all killmails after a certain timestamp

    Parameters
    ----------
    url : str
        The zkillboard.com url to fetch kills from.
    start : datetime
        The oldest allowed timestamp for a valid killmail.
    """

    reached_end = False

    for page in range(1, 101):
        # Make sure we fetch at most one page per second
        kill_hashes, _ = await asyncio.gather(get_kill_page(url, page), asyncio.sleep(1))

        async for kill in gather_kills(kill_hashes):
            if "killmail_time" in kill:
                # Check if we can stop
                time = datetime.strptime(kill['killmail_time'], '%Y-%m-%dT%H:%M:%SZ')
                if start > time:
                    reached_end = True

                yield kill

        if reached_end:
            break


# Alternative ways to get bulk killmails
async def get_everef_kills(day_string):
    url = f"https://data.everef.net/killmails/{day_string[:4]}/killmails-{day_string[:4]}-{day_string[4:6]}-{day_string[6:8]}.tar.bz2"
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    with tarfile.open(fileobj=BytesIO(data), mode='r:bz2') as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                yield json.loads(tar.extractfile(member).read())
                    return

            await asyncio.sleep(0.25 * (attempt + 1) ** 3)  # Cubic backoff

    raise ValueError(f"Could not fetch data from Everef!")


async def get_days():
    url = "https://zkillboard.com/api/history/totals.json"
    return await get(url)


async def get_hashes(day):
    url = f"https://zkillboard.com/api/history/{day}.json"
    return await get(url)


@cached()
async def get_corporation_name(corporation_id):
    url = f"https://esi.evetech.net/latest/corporations/{corporation_id}/"
    return (await get(url))["name"]


@cached()
async def get_alliance_name(alliance_id):
    url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/"
    return (await get(url))["name"]


@cached()
async def get_character_name(character_id):
    url = f"https://esi.evetech.net/latest/characters/{character_id}/"
    return (await get(url))["name"]


async def get_item_price_history(type_id, region_id=10000002):
    url = f"https://esi.evetech.net/latest/markets/{region_id}/history/?datasource=tranquility&type_id={type_id}"
    return await get(url)


async def get_item_price(type_id):
    url = f"https://market.fuzzwork.co.uk/aggregates/?region=10000002&types={type_id}"
    return float((await get(url))[str(type_id)]["sell"]["min"])


@cached()
async def get_corp_name(corporation_id):
    url = f"https://esi.evetech.net/latest/corporations/{corporation_id}/"
    return (await get(url))["name"]


@cached()
async def get_alliance_name(alliance_id):
    url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/"
    return (await get(url))["name"]


@cached()
async def get_alliance_corporations(alliance_id):
    url = f"https://esi.evetech.net/latest/alliances/{alliance_id}/corporations/"
    return await get(url)


@cached()
async def get_corp_alliance(corporation_id):
    url = f"https://esi.evetech.net/latest/corporations/{corporation_id}/"
    return (await get(url)).get("alliance_id", 0)


@cached()
async def get_system_name(system_id):
    url = f"https://esi.evetech.net/latest/universe/systems/{system_id}/"
    return (await get(url))["name"]


@cached()
async def get_system_security(system_id):
    url = f"https://esi.evetech.net/latest/universe/systems/{system_id}/"
    return (await get(url))["security_status"]


@cached()
async def get_character_name(character_id):
    url = f"https://esi.evetech.net/latest/characters/{character_id}/"
    return (await get(url))["name"]


@cached()
async def get_character_corporation(character_id):
    url = f"https://esi.evetech.net/latest/characters/{character_id}/"
    return (await get(url))["corporation_id"]


@cached()
async def get_item_name(item_id):
    url = f"https://esi.evetech.net/latest/universe/types/{item_id}/"
    return (await get(url))["name"]


@cached()
async def get_corp_member_count(corporation_id):
    url = f"https://esi.evetech.net/latest/corporations/{corporation_id}/"
    return (await get(url))["member_count"]


@cached()
async def get_jumps(origin, destination):
    url = f"https://esi.evetech.net/latest/route/{origin}/{destination}/"
    return len(await get(url))


async def get_days():
    url = "https://zkillboard.com/api/history/totals.json"
    return await get(url)


async def get_hashes(day):
    url = f"https://zkillboard.com/api/history/{day}.json"
    return await get(url)


async def get_item_data(type_id):
    url = f"https://esi.evetech.net/latest/universe/types/{type_id}/"
    return await get(url)


async def get_group_data(group_id):
    url = f"https://esi.evetech.net/latest/universe/groups/{group_id}/"
    return await get(url)


async def get_group_id(type_id):
    return (await get_item_data(type_id))["group_id"]


async def get_category_id(type_id):
    return (await get_group_data(await get_group_id(type_id)))["category_id"]


async def get_dogma_attributes(type_id):
    out = {}
    for item in (await get_item_data(type_id))["dogma_attributes"]:
        out[int(item["attribute_id"])] = item["value"]
    return out


async def get_dogma_attribute(type_id, attribute_id):
    for attribute in (await get_item_data(type_id))["dogma_attributes"]:
        if attribute["attribute_id"] == attribute_id:
            return float(attribute["value"])


async def get_meta_level(type_id):
    return int(await get_dogma_attribute(type_id, 633))


async def is_heatable(type_id):
    return await get_dogma_attribute(type_id, 1211)


async def is_dda(type_id):
    return (await get_group_id(type_id)) == 645


async def is_miner(type_id):
    return (await get_group_id(type_id)) == 54


async def is_structure(type_id):
    return (await get_category_id(type_id)) == 65
