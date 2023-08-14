import asyncio
import math
from dataclasses import dataclass
import itertools
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


def get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu, **kwargs):
    sets_all = [DamageModSet(c) for c in mod_combinations(repeatable_mods, unique_mods, count)]
    sets_cpu_limited = [s for s in sets_all if s.cpu < max_cpu]
    xy = [(c.price, c.get_damage_multiplier(**kwargs)) for c in sets_cpu_limited]
    sets_cpu_price_limited = [s for s in sets_cpu_limited if min_price < s.price < max_price]

    sorter = RelationalSorter(xy)
    for x in sorted(sets_cpu_price_limited, key=lambda c: sorter((c.price, c.get_damage_multiplier(**kwargs))), reverse=True):
        yield x, sorter((x.price, x.get_damage_multiplier(**kwargs)))


async def gyros(count, min_price, max_price, max_cpu):
    unique_mods = [x async for x in get_abyssals_damage_mods(49730)]

    repeatable_mods = [
        DamageMod(16, 1.07, 0.93, *(await get_cheapest([518]))),
        DamageMod(30, 1.10, 0.90, *(await get_cheapest([519]))),
        DamageMod(27, 1.07, 0.92, *(await get_cheapest([520]))),
        DamageMod(18, 1.1, 0.90, *(await get_cheapest([21486]))),
        DamageMod(25, 1.08, 0.90, *(await get_cheapest([5933]))),
        DamageMod(20, 1.12, 0.89, *(await get_cheapest([13939, 15806]))),
    ]

    for item, effectiveness in itertools.islice(get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu), 20):
        print(item, effectiveness)


async def bcs(count, min_price, max_price, max_cpu, **kwargs):
    unique_mods = [x async for x in get_abyssals_damage_mods(49738)]

    repeatable_mods = [
        DamageMod(35, 1.07, 0.92, *(await get_cheapest([12274]))),
        DamageMod(40, 1.10, 0.90, *(await get_cheapest([22291]))),
        DamageMod(22, 1.1, 0.90, *(await get_cheapest([21484]))),
        DamageMod(31, 1.08, 0.90, *(await get_cheapest([16457]))),
        DamageMod(38, 1.1, 0.90, *(await get_cheapest([46270]))),
        DamageMod(24, 1.12, 0.89, *(await get_cheapest([15681, 13935, 13937, 28563, 15683]))),
    ]

    for item, effectiveness in itertools.islice(get_best(unique_mods, repeatable_mods, count, min_price, max_price, max_cpu, **kwargs), 20):
        print(item, effectiveness)

asyncio.run(bcs(3, 100_000_000, 500_000_000, 70, base_reload_ratio=0.720))

