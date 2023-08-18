import asyncio
import math
from dataclasses import dataclass

import aiohttp

from utils import RelationalSorter, get_urls


@dataclass
class DamageMod:
    cpu: float
    damage: float
    rof: float
    price: float
    identifier: str

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


class DamageModSet:
    @staticmethod
    def stacking(u):
        return math.exp(-(u / 2.67) ** 2)

    def __init__(self, damage_mods: list):
        self.damage_mods = damage_mods

    @property
    def damage_multiplier(self):
        return self.get_damage_multiplier()

    def get_damage_multiplier(self, base_reload_ratio=1):
        damage_increase = 1
        for x, value in enumerate(sorted([x.damage for x in self.damage_mods], reverse=True)):
            damage_increase *= (1 + ((value - 1) * self.stacking(x)))

        rof_time_decrease = 1
        for x, value in enumerate(sorted([x.rof for x in self.damage_mods])):
            rof_time_decrease *= 1 + ((value - 1) * self.stacking(x))

        rof_time_decrease = (base_reload_ratio * rof_time_decrease + (1-base_reload_ratio))

        return damage_increase / rof_time_decrease

    @property
    def cpu(self):
        return sum([x.cpu for x in self.damage_mods])

    @property
    def price(self):
        return sum([x.price for x in self.damage_mods])

    def __str__(self):
        return f"CPU: {self.cpu} Damage: {self.damage_multiplier} Price: {self.price} {[x.identifier for x in self.damage_mods]}"


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

                    yield DamageMod(0, 0, 0, c_price, f"{i_item_id}:{c_id}").from_attributes(
                        item_attributes["dogma_attributes"])


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


def get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu, iterations=20, **kwargs):
    sets_all = [DamageModSet(c) for c in mod_combinations(repeatable_mods, unique_mods, count)]
    sets_cpu_limited = [s for s in sets_all if s.cpu < max_cpu]
    xy = [(c.price, c.get_damage_multiplier(**kwargs)) for c in sets_cpu_limited]
    sets_cpu_price_limited = [s for s in sets_cpu_limited if min_price < s.price < max_price]

    sorter = RelationalSorter(xy)
    for x in sorted(sets_cpu_price_limited, key=lambda c: sorter((c.price, c.get_damage_multiplier(**kwargs))), reverse=True)[:iterations]:
        yield x, sorter((x.price, x.get_damage_multiplier(**kwargs)))


async def gyros(count, min_price, max_price, max_cpu):
    print("Fetching contracts (1/3)")
    unique_mods = [x async for x in get_abyssals_damage_mods(49730)]

    print("Fetching normal mods (2/3)")
    repeatable_mods = [
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([518]))),  # Basic
        DamageMod(30, 1.10, 0.90, *(await get_cheapest([519]))),  # T2
        DamageMod(27, 1.07, 0.92, *(await get_cheapest([520]))),  # T1
        DamageMod(18, 1.1, 0.90, *(await get_cheapest([21486]))),  # Kindred
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5933]))),  # Compact
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([13939, 15806]))),  # Faction
    ]

    print("Finding best Set (3/3)")
    for item, effectiveness in get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu):
        print(item, effectiveness)


async def ballistics(count, min_price, max_price, max_cpu):
    print("Fetching contracts (1/3)")
    unique_mods = [x async for x in get_abyssals_damage_mods(49738)]

    print("Fetching normal mods (2/3)")
    repeatable_mods = [
        DamageMod(22, 1.10, 0.9, *(await get_cheapest([21484]))),  # Full Duplex
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([12274]))),  # T1
        DamageMod(31, 1.08, 0.90, *(await get_cheapest([16457]))),  # Compact
        DamageMod(40, 1.1, 0.90, *(await get_cheapest([22291]))),  # T2
        DamageMod(38, 1.1, 0.90, *(await get_cheapest([46270]))),  # Kaatara's
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([15681, 13935, 13937, 28563, 15683]))),  # Faction
    ]

    print("Finding best Set (3/3)")
    for item, effectiveness in get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu):
        print(item, effectiveness)


async def heatsinks(count, min_price, max_price, max_cpu):
    print("Fetching contracts (1/3)")
    unique_mods = [x async for x in get_abyssals_damage_mods(49726)]

    print("Fetching normal mods (2/3)")
    repeatable_mods = [
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([2363]))),  # T1
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5849]))),  # Compact
        DamageMod(30, 1.1, 0.90, *(await get_cheapest([2364]))),  # T2
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([1893]))),  # Basic
        DamageMod(18, 1.1, 0.9, *(await get_cheapest([23902]))),  # Trebuchet
        DamageMod(29, 1.1, 0.9, *(await get_cheapest([23902]))),  # Tahron's
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([15810, 13943, 15808]))),  # Faction
    ]

    print("Finding best Set (3/3)")
    for item, effectiveness in get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu):
        print(item, effectiveness)


async def magstabs(count, min_price, max_price, max_cpu):
    print("Fetching contracts (1/3)")
    unique_mods = [x async for x in get_abyssals_damage_mods(49722)]

    print("Fetching normal mods (2/3)")
    repeatable_mods = [
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([9944]))),  # T1
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5849]))),  # Compact
        DamageMod(30, 1.1, 0.90, *(await get_cheapest([10190]))),  # T2
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([10188]))),  # Basic
        DamageMod(18, 1.1, 0.9, *(await get_cheapest([22919]))),  # Monopoly
        DamageMod(29, 1.1, 0.9, *(await get_cheapest([44113, 44114]))),  # Kaatara's, Torelle's
        DamageMod(24, 1.14, 0.9, *(await get_cheapest([15416]))),  # Naiyon's
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([15895, 13945]))),  # Faction
    ]

    print("Finding best Set (3/3)")
    for item, effectiveness in get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu):
        print(item, effectiveness)


async def entropics(count, min_price, max_price, max_cpu):
    print("Fetching contracts (1/3)")
    unique_mods = [x async for x in get_abyssals_damage_mods(49734)]

    print("Fetching normal mods (2/3)")
    repeatable_mods = [
        DamageMod(27, 1.09, 0.96, *(await get_cheapest([9944]))),  # T1
        DamageMod(25, 1.10, 0.95, *(await get_cheapest([5849]))),  # Compact
        DamageMod(30, 1.13, 0.94, *(await get_cheapest([10190]))),  # T2
        DamageMod(23, 1.14, 0.93, *(await get_cheapest([52244]))),  # Faction
    ]

    print("Finding best Set (3/3)")
    for item, effectiveness in get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu):
        print(item, effectiveness)


asyncio.run(ballistics(3, 100000000, 300000000, 84))
