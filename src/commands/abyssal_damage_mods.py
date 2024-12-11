import asyncio
import math

from async_lru import alru_cache
from discord.ext import commands

from network import get_item_price, get_item_name, get
from utils import RelationalSorter, unix_style_arg_parser, command_error_handler, isk
from utils import convert


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
        for attribute_id, value in attributes.items():
            if attribute_id == 50:
                self.cpu = value
            if attribute_id == 64:
                self.damage = value
            if attribute_id == 213:
                self.damage = value
            if attribute_id == 204:
                self.rof = value
        return self

    def __str__(self):
        return asyncio.run(self.async_str())

    async def async_str(self, number=1):
        if self.module_id is None:
            return await get_item_name(self.type_id)
        else:
            return (f"[Abyssal Module {number}](https://mutamarket.com/modules/{self.module_id}) "
                    f"Contract: <url=contract:30000142//{self.contract_id}>Contract {self.contract_id}</url>")


class DamageModSet:
    @staticmethod
    def stacking(u):
        return math.exp(-(u / 2.67) ** 2)

    def __init__(self, damage_mods: list):
        self.damage_mods = damage_mods

    @property
    def damage_multiplier(self):
        return self.get_damage_multiplier()

    def get_damage_multiplier(self, uptime=1, rof_rig="", damage_rig=""):

        damage_multipliers = [x.damage for x in self.damage_mods]
        if damage_rig.lower() == "t1":
            damage_multipliers.append(1.1)
        if damage_rig.lower() == "t2":
            damage_multipliers.append(1.15)
        if damage_rig.lower() == "t1x2":
            damage_multipliers.extend([1.1, 1.1])

        damage_increase = 1
        for x, value in enumerate(sorted(damage_multipliers, reverse=True)):
            damage_increase *= (1 + ((value - 1) * self.stacking(x)))

        rof_multipliers = [x.rof for x in self.damage_mods]
        if rof_rig.lower() == "t1":
            rof_multipliers.append(1 / 1.1)
        if rof_rig.lower() == "t2":
            rof_multipliers.append(1 / 1.15)
        if rof_rig.lower() == "t1x2":
            rof_multipliers.extend([1 / 1.1, 1 / 1.1])

        rof_time_decrease = 1
        for x, value in enumerate(sorted(rof_multipliers)):
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
        out = f"**CPU: {self.cpu:.2f} Damage: {self.damage_multiplier:.3f} Price: {isk(self.price)}" + \
              ("**" if efficiency is None else f" (Efficiency: {efficiency})**\n")
        out += "\n".join([await x.async_str(i + 1) for i, x in enumerate(self.damage_mods)])
        return out


async def get_abyssals_mutamarket(type_id: int):
    url = f"https://mutamarket.com/api/modules/type/{type_id}/item-exchange/contracts-only/"
    item_data = await get(url)
    for item in item_data:
        if not (contract := item.get("contract")):
            continue

        if not contract.get("type") == "item_exchange":
            continue

        if not contract.get("region_id", 10000002) == 10000002:
            continue

        if not contract.get("plex_count", 0) == 0:
            continue

        if contract.get("asking_for_items", True):
            continue

        attributes = {a.get("id"): a.get("value") for a in item.get("mutated_attributes", [])}

        yield DamageMod(
            price=contract.get("price"),
            type_id=item.get("mutator_type_id"),
            module_id=item.get("id"),
            contract_id=contract.get("id"),
            attributes=attributes,
        )


async def get_price_with_id(type_id):
    return await get_item_price(type_id), type_id


async def get_cheapest(item_ids):
    items = await asyncio.gather(*[get_price_with_id(item_id) for item_id in item_ids])
    return min(items, key=lambda item: item[0])


def module_combinations(repeatable_mods, unique_mods, count) -> list[list[DamageMod]]:
    if count == 1:
        for m in repeatable_mods + unique_mods:
            yield [m]
    else:
        for i, m in enumerate(repeatable_mods):
            for y in module_combinations(repeatable_mods[i:], unique_mods, count - 1):
                yield [m] + y

        for i, m in enumerate(unique_mods):
            for y in module_combinations([], unique_mods[i + 1:], count - 1):
                yield [m] + y


def filter_modules(modules: list[DamageMod]) -> list[DamageMod]:
    """filter out any modules that are strictly worse than some other modules"""
    modules_to_remove = set()

    for module in modules:
        for other_module in modules:
            if (module.cpu > other_module.cpu and
                    module.rof > other_module.rof and
                    module.damage < other_module.damage and
                    module.price > other_module.price):
                modules_to_remove.add(module)
                break

    # Remove modules
    modules = list(set(modules) - modules_to_remove)

    return modules


def best_sets(
        unique_mods,
        repeatable_mods,
        count,
        min_price,
        max_price,
        max_cpu,
        results=5,
        **kwargs
) -> list[tuple[DamageModSet, float]]:
    """return the best module sets based on all possible module sets, as well as their relative grading"""
    sorting_points = []
    usable_sets = []
    for combination in module_combinations(repeatable_mods, unique_mods, count):

        damage_mod_set = DamageModSet(combination)
        if damage_mod_set.cpu < max_cpu:
            sorting_points.append(
                (
                    float(damage_mod_set.price),
                    float(damage_mod_set.get_damage_multiplier(**kwargs))
                )
            )
            if min_price < damage_mod_set.price < max_price:
                usable_sets.append(damage_mod_set)

    sorter = RelationalSorter(sorting_points)

    for x in sorted(
            usable_sets,
            key=lambda c: sorter((c.price, c.get_damage_multiplier(**kwargs))),
            reverse=True
    )[:results]:
        yield x, sorter((x.price, x.get_damage_multiplier(**kwargs)))


async def send_best(ctx, args, unique_getter, repeatable_getter):
    # Parse arguments
    arguments = unix_style_arg_parser(args)

    try:
        slots = int(arguments[""][0])
        max_cpu = float(arguments[""][1])
        min_price = convert(arguments[""][2])
        max_price = convert(arguments[""][3])
    except (KeyError, IndexError, ValueError):
        # Return early if the arguments can't be parsed
        await ctx.send("Could not parse your arguments!")
        return

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

    if "rof_rig" in arguments:
        rof_rig = arguments["rof_rig"][0]
    elif "r" in arguments:
        rof_rig = arguments["r"][0]
    else:
        rof_rig = ""

    if "damage_rig" in arguments:
        damage_rig = arguments["damage_rig"][0]
    elif "d" in arguments:
        damage_rig = arguments["d"][0]
    else:
        damage_rig = ""

    # Fetch modules
    repeatable_mods = await repeatable_getter()
    unique_mods = await unique_getter()

    # Filter modules
    unique_mods = filter_modules(unique_mods)

    # Return early if there are to many combinations
    if (len(unique_mods) + len(repeatable_mods)) ** slots > 80e9:
        await ctx.send("There are to many combinations your requirements!\n "
                       "Consider reducing the price range or amount of slots.")
        return

    # Make printout
    has_set = False
    for itemset, effectiveness in best_sets(
            unique_mods, repeatable_mods, slots, min_price, max_price, max_cpu,
            results=count, uptime=uptime, rof_rig=rof_rig, damage_rig=damage_rig
    ):
        has_set = True
        ret = await itemset.async_str(effectiveness)
        await ctx.send(ret)

    if not has_set:
        await ctx.send("No combinations found for these requirements!")


@alru_cache(ttl=300)
async def ballistics_unique():
    return [x async for x in get_abyssals_mutamarket(49738)]


@alru_cache(ttl=300)
async def entropics_unique():
    return [x async for x in get_abyssals_mutamarket(49734)]


@alru_cache(ttl=300)
async def gyros_unique():
    return [x async for x in get_abyssals_mutamarket(49730)]


@alru_cache(ttl=300)
async def heatsinks_unique():
    return [x async for x in get_abyssals_mutamarket(49726)]


@alru_cache(ttl=300)
async def magstabs_unique():
    return [x async for x in get_abyssals_mutamarket(49722)]


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


@commands.command()
@command_error_handler
async def ballistics(ctx, *args):
    """
    !ballistics <slots> <max_cpu> <min_price> <max_price>
        [-u|--uptime <value>]
        [-c|--count <value>]
        [-r | -rof_rig <t1, t2, t1x2>]
        [-d | -damage_rig <t1, t2, t1x2>]
    """
    await send_best(ctx, args, ballistics_unique, ballistics_repeatable)


@commands.command()
@command_error_handler
async def entropics(ctx, *args):
    """
    !entropics <slots> <max_cpu> <min_price> <max_price>
        [-u|--uptime <value>]
        [-c|--count <value>]
        [-r | -rof_rig <t1, t2, t1x2>]
        [-d | -damage_rig <t1, t2, t1x2>]
    """
    await send_best(ctx, args, entropics_unique, entropics_repeatable)


@commands.command()
@command_error_handler
async def gyros(ctx, *args):
    """
    !gyros <slots> <max_cpu> <min_price> <max_price>
        [-u|--uptime <value>]
        [-c|--count <value>]
        [-r | -rof_rig <t1, t2, t1x2>]
        [-d | -damage_rig <t1, t2, t1x2>]
    """
    await send_best(ctx, args, gyros_unique, gyros_repeatable)


@commands.command()
@command_error_handler
async def heatsinks(ctx, *args):
    """
    !heatsinks <slots> <max_cpu> <min_price> <max_price>
        [-u|--uptime <value>]
        [-c|--count <value>]
        [-r | -rof_rig <t1, t2, t1x2>]
        [-d | -damage_rig <t1, t2, t1x2>]
    """
    await send_best(ctx, args, heatsinks_unique, heatsinks_repeatable)


@commands.command()
@command_error_handler
async def magstabs(ctx, *args):
    """
    !magstabs <slots> <max_cpu> <min_price> <max_price>
        [-u|--uptime <value>]
        [-c|--count <value>]
        [-r | -rof_rig <t1, t2, t1x2>]
        [-d | -damage_rig <t1, t2, t1x2>]
    """
    await send_best(ctx, args, magstabs_unique, magstabs_repeatable)


async def setup(bot):
    bot.add_command(ballistics)
    bot.add_command(entropics)
    bot.add_command(gyros)
    bot.add_command(heatsinks)
    bot.add_command(magstabs)
