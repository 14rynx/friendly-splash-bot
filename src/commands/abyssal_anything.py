import asyncio
import itertools
import logging

from discord.ext import commands

from network import get, get_dogma_attributes
from utils import convert, command_error_handler, unix_style_arg_parser

# Configure the logger
logger = logging.getLogger('discord.utils')
logger.setLevel(logging.INFO)

stat_dictionary = {
    "price": 0,
    "hps": 420001,
    "hpgj": 420002,
    "gjs": 420003,
    "cpu": 50,
    "pg": 30,
    "power": 30,
    "powergrid": 30,
    "cap": 6,
    "speed": 20,
    "power": 30,
    "cpu": 50,
    "sig": 554,
    "signature": 554,
    "duration": 73,
    "em_resonance": 974,
    "explosive_resonance": 975,
    "kinetic_resonance": 976,
    "thermal_resonance": 977,
    "siegeMissileDamageBonus": 2306,
    "siegeTurretDamageBonus": 2307,
    "siegeLocalLogisticsDurationBonus": 2346,
    "siegeLocalLogisticsAmountBonus": 2347,
    "range": 54,
    "rep": 84,
    "reload": 1795,
    "boost": 68,
    "neut": 97,
    "ct": 90,
    "hp": 9,
    "cap_reduction": 147,
    "mass": 796,
    "extra_armor": 1159,
    "extra_cap": 67,
    "neut_resist": 2267,
    "extra_shield": 72,
    "signatureRadiusAdd": 983,
}

module_dictionary = {
    "10000mn": 56305,
    "100mn": 47757,
    "10mn": 47753,
    "1mn": 47749,
    "50000mn": 56306,
    "500mn": 47745,
    "50mn": 47408,
    "5mn": 47740,
    "adc": 52230,
    "dcu": 52227,
    "siege": 56313,
    "web": 47702,
    "point": 47736,
    "scram": 47732,
    "caar": 56308,
    "casb": 56310,
    "car": 56307,
    "cneut": 56312,
    "capital_neut": 56312,
    "cnos": 56311,
    "ccapital_nos": 56311,
    "csb": 56309,
    "hneut": 47832,
    "heavy_neut": 47832,
    "hnos": 48427,
    "heavy_nos": 48427,
    "hpoint": 56304,
    "heavy_point": 56304,
    "hscram": 56303,
    "heavy_scram": 56303,
    "laar": 47846,
    "lasb": 47838,
    "1600mm": 47820,
    "lar": 47777,
    "lbat": 48439,
    "large_battery": 48439,
    "lsb": 47789,
    "lse": 47808,
    "maar": 47844,
    "masb": 47836,
    "800mm": 47817,
    "mar": 47773,
    "mbat": 48435,
    "medium_battery": 48435,
    "mneut": 47828,
    "medium_neut": 47828,
    "mnos": 48423,
    "medium_nos": 48423,
    "msb": 47785,
    "mse": 47804,
    "saar": 47842,
    "400mm": 47812,
    "sar": 47769,
    "sbat": 48431,
    "small_battery": 48431,
    "sneut": 47824,
    "small_neut": 47824,
    "snos": 48419,
    "small_nos": 48419,
    "ssb": 47781,
    "sse": 47800,
    "xlasb": 47840,
    "xlsb": 47793
}


class Module:
    def __init__(self, json):
        self.type_id = json['type_id']
        self.item_id = json["id"]
        self.mutator_type_id = json['mutator_type_id']
        self.source_type_id = json['source_type_id']
        self.contract_id = json['latest_contract_id']

        # Make dictionary with attributes
        self.mutated_attributes = {}
        for attribute in json.get("attributes"):
            self.mutated_attributes[attribute["attribute_id"]] = float(attribute["value"])

        self.basic_attributes = {}

        # Calculate shield booster stats
        try:
            self.mutated_attributes[420001] = self.mutated_attributes[68] / self.mutated_attributes[73] * 1000
            self.mutated_attributes[420002] = self.mutated_attributes[68] / self.mutated_attributes[6]
            self.mutated_attributes[420003] = self.mutated_attributes[6] / self.mutated_attributes[73] * 1000
        except KeyError:
            pass

        # Add price stat
        self.mutated_attributes[0] = json.get("contract").get("unified_price")

    @property
    def attributes(self):
        attrs = self.basic_attributes
        attrs.update(self.mutated_attributes)
        return attrs

    async def fetch(self):
        for attribute in await get_dogma_attributes(self.source_type_id):
            if attribute["attribute_id"] not in self.basic_attributes:
                self.basic_attributes[attribute["attribute_id"]] = float(attribute["value"])

    def url(self, number=1):
        return f"[Abyssal Module {number}](https://mutamarket.com/modules/{self.item_id})"


async def get_abyssals(type_id: int):
    url = f"https://mutamarket.com/api/modules/type/{type_id}/item-exchange/contracts-only/"
    item_data = await get(url)

    modules = [Module(json=j) for j in item_data]
    tasks = [m.fetch() for m in modules]
    await asyncio.gather(*tasks)

    return modules


def combine_stats(combination):
    # Calculate combination stats
    stats = {}
    for module in combination:
        for aid, stat in module.attributes.items():
            stats[aid] = stats.get(aid, 0) + stat

    return stats


def parse_module(module_string):
    if module_string.lower() in module_dictionary:
        return module_dictionary[module_string.lower()]
    else:
        return int(module_string)


def parse_stat(stat_string):
    if stat_string.lower() in stat_dictionary:
        return stat_dictionary[stat_string.lower()]
    else:
        return int(stat_string)


@commands.command()
@command_error_handler
async def multi(ctx, *args):
    """"""
    # Parse arguments
    arguments = unix_style_arg_parser(args)

    # Parse modules to use
    module_ids = [parse_module(m) for m in arguments[""]]
    del arguments[""]

    # Parse sorting / filtering to use
    stats_min = {}
    stats_max = {}
    sort_by = 0
    largest_first = False

    for stat, values in arguments.items():
        # Parse stat_id
        stat_id = parse_stat(stat)
        last = stat_id

        state = "keyword"
        for i, value in enumerate(values):
            if state == "keyword":
                keyword = value.lower()
                if keyword == "max":
                    state = "value_max"
                elif keyword == "min":
                    state = "value_min"
                elif keyword == "sort":
                    sort_by = last
                    state = "sort"
                elif keyword == "only":
                    state = "only"
                continue

            if state == "value_max":
                if stat_id in stats_max:
                    stats_max[last].append(convert(value))
                else:
                    stats_max[last] = [convert(value)]
                state = "keyword"
                continue

            elif state == "value_min":
                if last in stats_min:
                    stats_min[last].append(convert(value))
                else:
                    stats_min[last] = [convert(value)]
                state = "keyword"
                continue

            elif state == "sort":
                largest_first = "desc" in value.lower()
                state = "keyword"
                continue

            elif state == "only":
                last = (stat_id, parse_module(value))
                state = "keyword"
                continue

    logger.info(f"Filter\n - Min: {stats_min}\n - Max: {stats_max}\n - Sort by {sort_by}")
    # Fetch modules
    tasks = [get_abyssals(type_id) for type_id in module_ids]
    modules = await asyncio.gather(*tasks)

    logger.info("All Modules:" + " ".join([str(len(m)) for m in modules]))

    # Check if individual modules satisfy requirements
    usable_modules = []
    for module_group in modules:
        group_usable_modules = []
        for module in module_group:
            usable = True
            for requirement, values in stats_min.items():
                for value in values:
                    if type(requirement) is tuple:
                        stat_id, module_id = requirement
                        if module.type_id == module_id and module.attributes[stat_id] < value:
                            usable = False

            for requirement, values in stats_max.items():
                for value in values:
                    if type(requirement) is tuple:
                        stat_id, module_id = requirement
                        if module.type_id == module_id and module.attributes[stat_id] > value:
                            usable = False

            if usable:
                group_usable_modules.append(module)

        usable_modules.append(group_usable_modules)

    logger.info("Usable Modules:" + " ".join([str(len(m)) for m in usable_modules]))

    usable_combinations = []
    # Filter combinations by stats
    for combination in itertools.product(*usable_modules):

        usable = True

        stats = combine_stats(combination)

        # Check if combination satisfies requirements
        for requirement, values in stats_min.items():
            for value in values:
                if type(requirement) is int:
                    stat_id = requirement
                    if stat_id in stats:
                        if stats[stat_id] < value:
                            usable = False

        for requirement, values in stats_max.items():
            for value in values:
                if type(requirement) is int:
                    stat_id = requirement
                    if stat_id in stats:
                        if stats[stat_id] > value:
                            usable = False

        if usable:
            usable_combinations.append(combination)

    logger.info(f"Usable combinations: {len(usable_combinations)}")

    # Build sorting functions
    def sort(combination):
        if type(sort_by) is int:
            stat_id = sort_by
            return combine_stats(combination)[stat_id]
        elif type(sort_by) is tuple:
            stat_id, module_id = sort_by
            for module in combination:
                if module.type_id == module_id:
                    return module.attributes[stat_id]

    # Make output
    for combination in sorted(usable_combinations, key=sort, reverse=largest_first)[:2]:
        urls = " ".join([m.url(i) for i, m in enumerate(combination)])

        # Name stats for output (unused)
        """async with aiohttp.ClientSession() as session:
            async with session.get("https://sde.hoboleaks.space/tq/dogmaattributes.json") as response:
                standard_dictionary = await response.json()

        stats = combine_stats(combination)"""
        logger.info(
            f"Result Modules {' '.join(['(' + str(m.type_id) + ' ' + str(m.mutator_type_id) + ')' for m in combination])}\n ")

        await ctx.send(f"## Modules\n{urls}\n")
    if len(usable_combinations) == 0:
        await ctx.send("Could not find any combinations that satisfy those requirements!")


async def setup(bot):
    bot.add_command(multi)
