import asyncio
import itertools
import logging

import aiohttp
from commands.multi_abyssals.classes import Module
from commands.multi_abyssals.dictionary import module_dictionary, stat_dictionary
from discord.ext import commands
from utils import convert
from utils import unix_style_arg_parser

# Configure the logger
logger = logging.getLogger('discord.multi')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


async def get_abyssals(type_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://mutamarket.com/modules/json/type/{type_id}/") as response:
            modules = [Module(json=j) for j in await response.json()]

            tasks = [m.fetch(session) for m in modules]
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
async def multi(ctx, *args):
    """"""
    try:
        # Parse arguments
        arguments = unix_style_arg_parser(args)

        logger.info(f"Arguments {arguments}")

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
    except ValueError:
        await ctx.send("Could not parse those arguments!")


async def setup(bot):
    bot.add_command(multi)
