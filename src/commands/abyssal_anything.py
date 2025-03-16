import asyncio
import heapq
import itertools
import logging

from discord.ext import commands

from network import get, get_dogma_attributes, get_item_name
from utils import convert, command_error_handler, unix_style_arg_parser

# Configure the logger
logger = logging.getLogger('discord.utils')
logger.setLevel(logging.INFO)


class Entity:
    def __init__(self, some_id, full_name, abbreviation, *other_names):
        self.some_id = some_id
        self.full_name = full_name
        self.abbreviation = abbreviation

        if type(other_names) is str:
            self.other_names = [other_names]
        else:
            self.other_names = list(other_names)

        if "Abyssal" in full_name:
            self.other_names.append(full_name.replace("Abyssal", "").replace("  ", " "))

    def names(self):
        return self.full_name, self.abbreviation


class EntityRegistry:
    def __init__(self):
        self.id_to_entity = {}  # Maps ID -> Module
        self.name_to_id = {}  # Maps any name variant -> ID

    def add(self, entity):
        """Adds a new module and updates the lookup tables."""
        self.id_to_entity[entity.some_id] = entity

        # Map all names to this module's ID
        for name in entity.names():
            self.name_to_id[name.lower()] = entity.some_id

    def get_id(self, name):
        if (nl := name.lower()) in self.name_to_id:
            return self.name_to_id[nl]
        else:
            return int(name)

    def get_entity(self, name):
        return self.id_to_entity[self.get_id(name)]

    def get_name(self, some_id: int):
        if some_id in self.id_to_entity:
            return self.id_to_entity[some_id].full_name
        else:
            return f"Id: {some_id}"


module_registry = EntityRegistry()
module_registry.add(Entity(56305, "10000mn Abyssal Afterburner", "10000mn"))
module_registry.add(Entity(47757, "100mn Abyssal Afterburner", "100mn"))
module_registry.add(Entity(47753, "10mn Abyssal Afterburner", "10mn"))
module_registry.add(Entity(47749, "1mn Abyssal Afterburner", "1mn"))
module_registry.add(Entity(56306, "50000mn Abyssal Microwarpdrive", "50000mn"))
module_registry.add(Entity(47745, "500mn Abyssal Microwarpdrive", "500mn"))
module_registry.add(Entity(47408, "50mn Abyssal Microwarpdrive", "50mn"))
module_registry.add(Entity(47740, "5mn Abyssal Microwarpdrive", "5mn"))
module_registry.add(Entity(52230, "Abyssal Assault Damage Control", "adc"))
module_registry.add(Entity(52227, "Abyssal Damage Control", "dcu"))
module_registry.add(Entity(56313, "Abyssal Siege Module", "siege"))
module_registry.add(Entity(47702, "Abyssal Stasis Webifier", "web"))
module_registry.add(Entity(47736, "Abyssal Warp Disruptor", "point", "disruptor"))
module_registry.add(Entity(47732, "Warp Scrambler", "scram"))
module_registry.add(Entity(56308, "Capital Abyssal Ancillary Armor Repairer", "caar"))
module_registry.add(Entity(56310, "Capital Abyssal Ancillary Shield Booster", "casb"))
module_registry.add(Entity(56307, "Capital Abyssal Armor Repairer", "car"))
module_registry.add(Entity(56312, "Capital Abyssal Energy Neutralizer", "cneut"))
module_registry.add(Entity(56311, "Capital Abyssal Nosferatu", "cnos"))
module_registry.add(Entity(56309, "Capital Abyssal Shield Booster", "csb"))
module_registry.add(Entity(47832, "Heavy Abyssal Energy Neutralizer", "hneut"))
module_registry.add(Entity(48427, "Heavy Abyssal Nosferatu", "hnos"))
module_registry.add(Entity(56304, "Heavy Abyssal Warp Disruptor", "hpoint"))
module_registry.add(Entity(56303, "Heavy Abyssal Warp Scrambler", "hscram"))
module_registry.add(Entity(47846, "Large Abyssal Ancillary Armor Repairer", "laar"))
module_registry.add(Entity(47838, "Large Abyssal Ancillary Shield Booster", "lasb"))
module_registry.add(Entity(47820, "Large Abyssal Armor Plates", "1600mm", "1600mm"))
module_registry.add(Entity(47777, "Large Abyssal Armor Repairer", "LAR", "lar"))
module_registry.add(Entity(48439, "Large Abyssal Cap Battery", "lbat"))
module_registry.add(Entity(47789, "Large Abyssal Shield Booster", "LSB", "lsb"))
module_registry.add(Entity(47808, "Large Abyssal Shield Extender", "LSE", "lse"))
module_registry.add(Entity(47844, "Medium Abyssal Ancillary Armor Repairer", "maar"))
module_registry.add(Entity(47836, "Medium Abyssal Ancillary Shield Booster", "masb"))
module_registry.add(Entity(47817, "Medium Abyssal Armor Plates", "800mm"))
module_registry.add(Entity(47773, "Medium Abyssal Armor Repairer", "mar"))
module_registry.add(Entity(48435, "Medium Abyssal Cap Battery", "mbat"))
module_registry.add(Entity(47828, "Medium Abyssal Energy Neutralizer", "mneut"))
module_registry.add(Entity(48423, "Medium Abyssal Nosferatu", "mnos"))
module_registry.add(Entity(47785, "Medium Abyssal Shield Booster", "msb"))
module_registry.add(Entity(47804, "Medium Abyssal Shield Extender", "mse"))
module_registry.add(Entity(47842, "Small Abyssal Ancillary Armor Repairer", "saar"))
module_registry.add(Entity(47812, "Small Abyssal Armor Plate", "400mm"))
module_registry.add(Entity(47769, "Small Abyssal Armor Repairer", "sar"))
module_registry.add(Entity(48431, "Small AbyssalBattery", "sbat"))
module_registry.add(Entity(47824, "Small Abyssal Energy Neutralizer", "sneut"))
module_registry.add(Entity(48419, "Small AbyssalNosferatu", "snos"))
module_registry.add(Entity(47781, "Small Abyssal Shield Booster", "ssb"))
module_registry.add(Entity(47800, "Small Abyssal Shield Extender", "sse"))
module_registry.add(Entity(47840, "X-Large Abyssal Ancillary Shield Booster", "xlasb"))
module_registry.add(Entity(47793, "X-Large Abyssal Shield Booster", "xlsb"))

stat_registry = EntityRegistry()
stat_registry.add(Entity(0, "Price", "price"))
stat_registry.add(Entity(50, "CPU Usage", "cpu"))
stat_registry.add(Entity(30, "Powergrid Usage", "pg", "power", "powergrid"))
stat_registry.add(Entity(6, "Capacitor Usage", "cap", "capacitor"))
stat_registry.add(Entity(20, "Speed Boost", "speed"))
stat_registry.add(Entity(554, "Signature Radius Multiplier", "sig", "signature", "sig_multiplier", "sig_mult"))
stat_registry.add(Entity(73, "Duration", "duration"))
stat_registry.add(Entity(974, "Hull EM Resonance", "em_resonance"))
stat_registry.add(Entity(975, "Hull Explosive Resonance", "explosive_resonance"))
stat_registry.add(Entity(976, "Hull Kinetic Resonance", "kinetic_resonance"))
stat_registry.add(Entity(977, "Hull Thermal Resonance", "thermal_resonance"))
stat_registry.add(Entity(2306, "Siege Damage (Missiles)", "siege_damage_missile"))
stat_registry.add(Entity(2307, "Siege Damage (Turrets)", "siege_damage_turret"))
stat_registry.add(Entity(2346, "Siege Logistics Duration", "siege_logistics_duration"))
stat_registry.add(Entity(2347, "Siege Logistics Amount", "siege_logistics_amount"))
stat_registry.add(Entity(54, "Range", "range"))
stat_registry.add(Entity(84, "Repair Amount", "rep"))
stat_registry.add(Entity(1795, "Reload Time", "reload"))
stat_registry.add(Entity(68, "Shield Boost Amount", "shield_boost"))
stat_registry.add(Entity(97, "Energy Neutralizer Amount", "neut_amount"))
stat_registry.add(Entity(97, "Energy Nosferatu Amount", "nos_amount"))
stat_registry.add(Entity(90, "Cap Transfer Amount", "cap_amount"))
stat_registry.add(Entity(9, "Hitpoints", "hp"))
stat_registry.add(Entity(147, "Capacitor Reduction", "cap_reduction"))
stat_registry.add(Entity(796, "Mass Increase", "mass", "mass_increase"))
stat_registry.add(Entity(1159, "Additional Armor", "extra_armor"))
stat_registry.add(Entity(67, "Additional Capacitor", "extra_cap"))
stat_registry.add(Entity(2267, "Energy Neutralizer Resistance", "neut_resist"))
stat_registry.add(Entity(72, "Additional Shield", "extra_shield"))
stat_registry.add(Entity(983, "Signature Radius Addition", "sig_add"))
stat_registry.add(Entity(420001, "HP per Second", "hp/s"))
stat_registry.add(Entity(420002, "HP per GJ", "hp/gj"))
stat_registry.add(Entity(420003, "GJ per Second", "gj/s"))


class Module:
    def __init__(self, json):
        self.type_id = json.get("type", {}).get("id")
        self.module_id = json.get("id")
        self.mutator_type_id = json.get("mutaplasmid", {}).get("id")
        self.source_type_id = json.get("source_type", {}).get("id")
        self.contract_id = json.get("contract", {}).get("id")
        self.type_name = None
        self.unique = True  # Hardcoded for now

        # Make dictionary with attributes
        self.mutated_attributes = {}
        for attribute in json.get("mutated_attributes"):
            self.mutated_attributes[attribute.get("id")] = float(attribute.get("value"))

        self.basic_attributes = {}

        # Add price stat
        valid = True
        if not (contract := json.get("contract")):
            valid = False

        if not contract.get("type") == "item_exchange":
            valid = False

        if not contract.get("region_id", 10000002) == 10000002:
            valid = False

        if not contract.get("plex_count", 0) == 0:
            valid = False

        if contract.get("asking_for_items", True):
            valid = False

        if valid:
            self.mutated_attributes[0] = json.get("contract", {}).get("price")
        else:
            self.mutated_attributes[0] = float("inf")

    def calculate_attributes(self, skill=5):
        attrs = self.basic_attributes
        attrs.update(self.mutated_attributes)

        # Calculate skill bonuses (assume all V)
        # https://wiki.eveuniversity.org/Fitting_skills#Advanced_Weapon_Upgrades
        for type_name in ["sse", "mse", "lse"]:
            if self.type_id == module_registry.get_id(type_name):
                attrs[stat_registry.get_id("pg")] *= 1 - 0.05 * skill

        for type_name in ["sbat", "mbat", "lbat"]:
            if self.type_id == module_registry.get_id(type_name):
                attrs[stat_registry.get_id("cpu")] *= 1 - 0.05 * skill

        # Add calculated Attributes
        try:
            attrs[stat_registry.get_id("hp/s")] = attrs[stat_registry.get_id("shield_boost")] / attrs[
                stat_registry.get_id("duration")] * 1000
        except KeyError:
            pass

        try:
            attrs[stat_registry.get_id("hp/gj")] = attrs[stat_registry.get_id("shield_boost")] / attrs[
                stat_registry.get_id("cap")]
        except KeyError:
            pass

        try:
            attrs[stat_registry.get_id("gj/s")] = attrs[stat_registry.get_id("cap")] / attrs[
                stat_registry.get_id("duration")] * 1000
        except KeyError:
            pass

        return attrs

    def __str__(self):
        if self.type_name is None:
            ret = f"Abyssal Type {self.type_id}\n"
        else:
            ret = self.type_name

        if self.unique:
            ret += "\n"
            ret += f"- [Mutamarket](https://mutamarket.com/modules/{self.module_id})\n"
            ret += f"- Contract: `<url=contract:30000142//{self.contract_id}>Contract {self.contract_id}</url>`"
        return ret


async def get_abyssals(type_id: int):
    url = f"https://mutamarket.com/api/modules/type/{type_id}/item-exchange/contracts-only/"
    item_data = await get(url)

    modules = [Module(json=j) for j in item_data]

    # Collect unique type_ids
    attribute_type_ids = {m.source_type_id for m in modules}
    name_type_ids = {m.type_id for m in modules}

    # Fetch all attributes and names in parallel
    attribute_data = await asyncio.gather(*(get_dogma_attributes(tid) for tid in attribute_type_ids))
    name_data = await asyncio.gather(*(get_item_name(tid) for tid in name_type_ids))

    # Map results
    attribute_map = dict(zip(attribute_type_ids, attribute_data))
    name_map = dict(zip(name_type_ids, name_data))

    # Distribute fetched data to modules
    for module in modules:
        attributes = attribute_map.get(module.source_type_id, [])
        for attribute_id, value in attributes.items():
            module.basic_attributes[attribute_id] = value

        module.type_name = name_map.get(module.type_id)

    return modules


def combine_stats(combination):
    # Calculate combination stats
    stats = {}
    for module in combination:
        for aid, stat in module.calculate_attributes().items():
            stats[aid] = stats.get(aid, 0) + stat

    return stats


def parse_arguments(arguments):
    # Parse modules to use
    module_ids = [module_registry.get_id(m) for m in arguments[""]]
    del arguments[""]

    # Parse sorting / filtering to use
    stats_min = {}
    stats_max = {}
    sort_by = 0
    largest_first = False

    for stat, values in arguments.items():
        # Parse stat_id
        stat_id = stat_registry.get_id(stat)
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
                stats_max[last] = convert(value)
                state = "keyword"
                continue

            elif state == "value_min":
                stats_min[last] = convert(value)
                state = "keyword"
                continue

            elif state == "sort":
                largest_first = "desc" in value.lower()
                state = "keyword"
                continue

            elif state == "only":
                last = (int(stat_id), module_registry.get_id(value))
                state = "keyword"
                continue

    return module_ids, stats_min, stats_max, sort_by, largest_first


def filter_individual_modules(modules, stats_max):
    for module in modules:
        attributes = module.calculate_attributes()

        usable = True
        for requirement, value in stats_max.items():
            if type(requirement) is tuple:
                stat_id, module_id = requirement
                if module.type_id == module_id and stat_id in attributes and attributes[stat_id] > value:
                    usable = False

            elif type(requirement) is int:
                stat_id = requirement
                if stat_id in attributes and attributes[stat_id] > value:
                    usable = False

        if usable:
            yield module


def filter_module_sets(module_groups, stats_min, stats_max):
    for combination in itertools.product(*module_groups):

        usable = True

        stats = combine_stats(combination)

        for requirement, value in stats_min.items():
            if type(requirement) is int:
                stat_id = requirement
                if stat_id in stats:
                    if stats[stat_id] < value:
                        usable = False

        for requirement, value in stats_max.items():
            if type(requirement) is int:
                stat_id = requirement
                if stat_id in stats:
                    if stats[stat_id] > value:
                        usable = False

        if usable:
            yield combination


def stats_to_str(stats, sign="="):
    ret = ""
    for requirement, value in stats.items():
        if type(requirement) is tuple:
            stat_id, type_id = requirement
            ret += f"- {stat_registry.get_name(stat_id)} {sign} {value} for Abyssal {type_id}\n"
        elif type(requirement) is int:
            stat_id = requirement
            ret += f"- {stat_registry.get_name(stat_id)} {sign} {value}\n"

    return ret


@commands.command()
@command_error_handler
async def multi(ctx, *args):
    """Searches for a set of multiple different abyssals with combined requirements.
    Usage:
        !multi <list of modules>
        <list of requirement arguments>

        - Modules can be passed by module ID or by abbreviations
        - Requirements have the following format:
            --<stat> [min|max] <value>
            --<stat> sort [asc|desc]
            --<stat> only <module> [min|max] <value>
            or any combination thereof
    """

    # Parse arguments
    try:
        arguments = unix_style_arg_parser(args)
        module_ids, stats_min, stats_max, sort_by, largest_first = parse_arguments(arguments)
    except Exception:
        await ctx.send("Could not parse arguments!")
        return
    else:
        await ctx.send(
            f"Finding combinations for\n"
            f"Min:\n{stats_to_str(stats_min, '>')}"
            f"Max:\n{stats_to_str(stats_max, '<')}"
            f"Sort by {stat_registry.get_name(sort_by)}"
        )

    # Fetch modules
    tasks = [get_abyssals(type_id) for type_id in module_ids]
    module_groups = await asyncio.gather(*tasks)

    # Prefilter each module group to satisfy requirements individually
    usable_module_groups = []
    for m in module_groups:
        usable_module_groups.append(filter_individual_modules(m, stats_max))

    # Filter for combined requirements
    combinations = filter_module_sets(usable_module_groups, stats_min, stats_max)

    # Build sorting functions
    if type(sort_by) is int:
        stat_id = sort_by

        def sort_function(combination):
            stat_value = combine_stats(combination)[stat_id]
            return stat_value if largest_first else -stat_value

    elif type(sort_by) is tuple:
        stat_id, module_id = sort_by

        def sort_function(combination):
            for module in combination:
                if module.type_id == module_id:
                    stat_value = module.calculate_attributes().get(stat_id, 0)
                    return stat_value if largest_first else -stat_value
                return 0

    # Make output
    best_sets = heapq.nlargest(
        3,
        combinations,
        key=sort_function,
    )

    # Make printout
    # Find printable stats
    printable_keys = {stat for stat in list(stats_min.keys()) + list(stats_max.keys()) if type(stat) is int} | {sort_by}

    has_set = False
    for combination in best_sets:
        has_set = True
        module_body = "\n".join(map(str, combination))

        printable_stats = {k: v for k, v in combine_stats(combination).items() if k in printable_keys}
        stats_body = stats_to_str(printable_stats)

        await ctx.send(
            f"## Modules\n{module_body}\nStats:\n{stats_body}"
        )

    if not has_set:
        await ctx.send("No combinations found for these requirements!")


async def setup(bot):
    bot.add_command(multi)
