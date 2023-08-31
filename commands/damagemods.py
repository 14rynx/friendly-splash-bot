import asyncio
import math
import ssl

import aiohttp
import certifi
from async_lru import alru_cache

from utils import RelationalSorter
from utils import get_urls, get_item_name
from utils import isk, convert


class DamageMod:
    def __init__(self, cpu=100, damage=1.0, rof=1.0, price=1e50, type_id=None, module_id=None, contract_id=None,
                 attributes=None):
        self.cpu = cpu
        self.damage = damage
        self.rof = rof
        self.price = price

        self.type_id = type_id
        self.module_id = module_id
        self.contract_id = contract_id

        if attributes is not None:
            self.from_attributes(attributes)

    def from_attributes(self, attributes):
        for attribute in attributes:
            if attribute["attribute_id"] == 50:
                self.cpu = attribute["value"]
            if attribute["attribute_id"] == 64:
                self.damage = attribute["value"]
            if attribute["attribute_id"] == 213:
                self.damage = attribute["value"]
            if attribute["attribute_id"] == 204:
                self.rof = attribute["value"]
        return self

    def __str__(self):
        return asyncio.run(self.async_str())

    async def async_str(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            if self.module_id is None:
                return await get_item_name(self.type_id, session)
            else:
                return (f"Abyssal {self.module_id} (D: {self.damage:.2f}, R: {self.rof:.2f}, C: {self.cpu:.2f})\n"
                        f"      Link: https://mutaplasmid.space/module/{self.module_id}/ \n"
                        f"      Contract: <url=contract:30000142//{self.contract_id}>Contract {self.contract_id}</url>")


class DamageModSet:
    @staticmethod
    def stacking(u):
        return math.exp(-(u / 2.67) ** 2)

    def __init__(self, damage_mods: list):
        self.damage_mods = damage_mods

    @property
    def damage_multiplier(self):
        return self.get_damage_multiplier()

    def get_damage_multiplier(self, uptime=1):
        damage_increase = 1
        for x, value in enumerate(sorted([x.damage for x in self.damage_mods], reverse=True)):
            damage_increase *= (1 + ((value - 1) * self.stacking(x)))

        rof_time_decrease = 1
        for x, value in enumerate(sorted([x.rof for x in self.damage_mods])):
            rof_time_decrease *= 1 + ((value - 1) * self.stacking(x))

        rof_time_decrease = (uptime * rof_time_decrease + (1 - uptime))

        return damage_increase / rof_time_decrease

    @property
    def cpu(self):
        return sum([x.cpu for x in self.damage_mods])

    @property
    def price(self):
        return sum([x.price for x in self.damage_mods])

    def __str__(self):
        return asyncio.run(self.async_str())

    async def async_str(self, efficiency=None):
        header = f"**CPU: {self.cpu:.2f} Damage: {self.damage_multiplier:.3f} Price: {isk(self.price)}" + \
                 ("**" if efficiency is None else f" (Efficiency: {efficiency})**")
        body = "\n".join([("   " + await x.async_str()) for x in self.damage_mods])
        return header + "\n" + body + "\n"


async def get_abyssals_damage_mods(type_id: int):
    async with aiohttp.ClientSession() as session:
        p_urls = [f"https://esi.evetech.net/latest/contracts/public/10000002/?page={page}" for page in range(1, 100)]
        async for page in get_urls(p_urls, session):

            # Sort out pages that don't exist
            if type(page) == dict and "error" in page:
                continue

            interesting_contracts = [contract for contract in page if contract["type"] == "item_exchange"]
            c_ids = [contract["contract_id"] for contract in interesting_contracts]
            c_urls = [f"https://esi.evetech.net/latest/contracts/public/items/{c_id}/" for c_id in c_ids]
            c_prices = [contract["price"] for contract in interesting_contracts]
            async for c_items, (c_id, c_price) in get_urls(c_urls, session, zip(c_ids, c_prices)):

                # Sort out empty contracts
                if not c_items:
                    continue

                # Sort out plex contracts
                if 44992 in [int(item["type_id"]) for item in c_items if "type_id" in item]:
                    continue

                i_ids = [(item['type_id'], item['item_id']) for item in c_items if
                         "type_id" in item and int(item["type_id"]) == type_id]
                i_urls = [f"https://esi.evetech.net/latest/dogma/dynamic/items/{i_type_id}/{i_item_id}/" for
                          i_type_id, i_item_id in i_ids]
                async for item_attributes, (i_type_id, i_item_id) in get_urls(i_urls, session, i_ids):
                    if "dogma_attributes" not in item_attributes:
                        continue

                    yield DamageMod(price=c_price, type_id=i_type_id, module_id=i_item_id, contract_id=c_id,
                                    attributes=item_attributes["dogma_attributes"])


async def get_cheapest(item_ids):
    cheapest_price = float("inf")
    cheapest_id = 0

    async with aiohttp.ClientSession() as session:
        urls = [f"https://market.fuzzwork.co.uk/aggregates/?region=10000002&types={i}" for i in item_ids]
        async for item_prices, item_id in get_urls(urls, session, item_ids):
            item_price = float(item_prices[str(item_id)]["sell"]["min"])
            if item_price < 100:
                continue
            if item_price < cheapest_price:
                cheapest_price = item_price
                cheapest_id = item_id

    return cheapest_price, cheapest_id


def mod_combinations(repeatable_mods, unique_mods, count):
    if count == 1:
        for m in repeatable_mods + unique_mods:
            yield [m]
    else:
        for i, m in enumerate(repeatable_mods):
            for y in mod_combinations(repeatable_mods[i:], unique_mods, count - 1):
                yield [m] + y

        for i, m in enumerate(unique_mods):
            for y in mod_combinations([], unique_mods[i + 1:], count - 1):
                yield [m] + y


def get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu, iterations=5, **kwargs):
    sets_all = [DamageModSet(c) for c in mod_combinations(repeatable_mods, unique_mods, count)]
    sets_cpu_limited = [s for s in sets_all if s.cpu < max_cpu]
    xy = [(c.price, c.get_damage_multiplier(**kwargs)) for c in sets_cpu_limited]
    sets_cpu_price_limited = [s for s in sets_cpu_limited if min_price < s.price < max_price]

    sorter = RelationalSorter(xy)
    for x in sorted(sets_cpu_price_limited, key=lambda c: sorter((c.price, c.get_damage_multiplier(**kwargs))),
                    reverse=True)[:iterations]:
        yield x, sorter((x.price, x.get_damage_multiplier(**kwargs)))


async def send_help_message(message, command):
    await message.channel.send(
        f"Usage:\n !{command} <slots> <max_cpu> <min_price> <max_price>")
    return


async def send_best(arguments, message, command, unique_getter, repeatable_getter):
    if "help" in arguments:
        await send_help_message(message, command)
        return

    try:
        slots = int(arguments[""][0])
        max_cpu = float(arguments[""][1])
        min_prie = convert(arguments[""][2])
        max_price = convert(arguments[""][3])
    except (KeyError, IndexError, ValueError):
        await send_help_message(message, command)
    else:
        if "count" in arguments:
            count = int(arguments["count"][0])
        elif "c" in arguments:
            count = int(arguments["c"][0])
        else:
            count = 3

        if "uptime" in arguments:
            uptime = float(arguments["uptime"][0])
        elif "u" in arguments:
            uptime = float(arguments["u"][0])
        else:
            uptime = 1.0

        await message.channel.send("Fetching normal modules...")
        repeatable_mods = await repeatable_getter()

        await message.channel.send("Fetching contract modules...")
        unique_mods = await unique_getter()

        ret = ""
        for itemset, effectiveness in get_best(unique_mods, repeatable_mods, slots, min_prie, max_price, max_cpu,
                                               iterations=count, uptime=uptime):
            ret += await itemset.async_str(effectiveness)

        if ret == "":
            ret = "No combinations found for these requirements!"

        await message.channel.send(ret)


@alru_cache(ttl=300)
async def ballistics_unique():
    return [x async for x in get_abyssals_damage_mods(49738)]


@alru_cache(ttl=300)
async def entropics_unique():
    return [x async for x in get_abyssals_damage_mods(49734)]


@alru_cache(ttl=300)
async def gyros_unique():
    return [x async for x in get_abyssals_damage_mods(49730)]


@alru_cache(ttl=300)
async def heatsinks_unique():
    return [x async for x in get_abyssals_damage_mods(49726)]


@alru_cache(ttl=300)
async def magstabs_unique():
    return [x async for x in get_abyssals_damage_mods(49722)]


@alru_cache(ttl=1800)
async def ballistics_repeatable():
    return [
        DamageMod(22, 1.10, 0.9, *(await get_cheapest([21484]))),  # Full Duplex
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([12274]))),  # T1
        DamageMod(31, 1.08, 0.90, *(await get_cheapest([16457]))),  # Compact
        DamageMod(40, 1.1, 0.90, *(await get_cheapest([22291]))),  # T2
        DamageMod(38, 1.1, 0.90, *(await get_cheapest([46270]))),  # Kaatara's
        DamageMod(24, 1.12, 0.89, *(await get_cheapest([15681, 13935, 13937, 28563, 15683]))),  # Faction
    ]


@alru_cache(ttl=1800)
async def entropics_repeatable():
    return [
        DamageMod(27, 1.09, 0.96, *(await get_cheapest([47908]))),  # T1
        DamageMod(25, 1.10, 0.95, *(await get_cheapest([47909]))),  # Compact
        DamageMod(30, 1.13, 0.94, *(await get_cheapest([47911]))),  # T2
        DamageMod(23, 1.14, 0.93, *(await get_cheapest([52244]))),  # Faction
    ]


@alru_cache(ttl=1800)
async def gyros_repeatable():
    return [
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([518]))),  # Basic
        DamageMod(30, 1.10, 0.90, *(await get_cheapest([519]))),  # T2
        DamageMod(27, 1.07, 0.92, *(await get_cheapest([520]))),  # T1
        DamageMod(18, 1.1, 0.90, *(await get_cheapest([21486]))),  # Kindred
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5933]))),  # Compact
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([13939, 15806]))),  # Faction
    ]


@alru_cache(ttl=1800)
async def heatsinks_repeatable():
    return [
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([2363]))),  # T1
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5849]))),  # Compact
        DamageMod(30, 1.1, 0.90, *(await get_cheapest([2364]))),  # T2
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([1893]))),  # Basic
        DamageMod(18, 1.1, 0.9, *(await get_cheapest([23902]))),  # Trebuchet
        DamageMod(29, 1.1, 0.9, *(await get_cheapest([23902]))),  # Tahron's
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([15810, 13943, 15808]))),  # Faction
    ]


@alru_cache(ttl=1800)
async def magstabs_repeatable():
    return [
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([9944]))),  # T1
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5849]))),  # Compact
        DamageMod(30, 1.1, 0.90, *(await get_cheapest([10190]))),  # T2
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([10188]))),  # Basic
        DamageMod(18, 1.1, 0.9, *(await get_cheapest([22919]))),  # Monopoly
        DamageMod(29, 1.1, 0.9, *(await get_cheapest([44113, 44114]))),  # Kaatara's, Torelle's
        DamageMod(24, 1.14, 0.9, *(await get_cheapest([15416]))),  # Naiyon's
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([15895, 13945]))),  # Faction
    ]


async def command_ballistics(arguments, message):
    await send_best(arguments, message, "ballistics", ballistics_unique, ballistics_repeatable)


async def command_entropics(arguments, message):
    await send_best(arguments, message, "entropics", entropics_unique, entropics_repeatable)


async def command_gyros(arguments, message):
    await send_best(arguments, message, "gyros", gyros_unique, gyros_repeatable)


async def command_heatsinks(arguments, message):
    await send_best(arguments, message, "heatsinks", heatsinks_unique, heatsinks_repeatable)


async def command_magstabs(arguments, message):
    await send_best(arguments, message, "magstabs", magstabs_unique, magstabs_repeatable)
