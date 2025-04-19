import asyncio
import functools
import heapq
import math
from typing import Any, Generator, Optional

from async_lru import alru_cache
from discord import Interaction, app_commands
from discord.ext import commands

from network import get_item_price, get
from utils import RelationalSorter, isk, slash_command_error_handler
from utils import convert


class DamageMod:
    def __init__(self, type_id, type_name, **kwargs):
        self.type_id = type_id
        self.type_name = type_name

        self.cpu = None
        self.damage = None
        self.rof = None

        if kwargs:
            self.add_stats(**kwargs)

        self.price = None

        self.unique = False
        self.module_id = None
        self.contract_id = None

    def add_stats(self, cpu=None, damage=None, rof=None):
        self.cpu = cpu
        self.damage = damage
        self.rof = rof

    def add_stats_from_attributes(self, attributes=None):
        for attribute_id, value in attributes.items():
            match attribute_id:
                case 50:
                    self.cpu = value
                case 64 | 213:
                    self.damage = value
                case 204:
                    self.rof = value
                case _:
                    pass
        return self

    def add_unique_instance(self, module_id, contract_id):
        self.unique = True
        self.module_id = module_id
        self.contract_id = contract_id

    async def fetch_price(self):
        if not self.unique:
            self.price = await get_item_price(self.type_id)

    def __str__(self):
        ret = self.type_name
        if self.unique:
            ret += "\n"
            ret += f"- [Mutamarket](https://mutamarket.com/modules/{self.module_id})\n"
            ret += f"- Contract: `<url=contract:30000142//{self.contract_id}>Contract {self.contract_id}</url>`"
        return ret


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
        out = f"CPU: {self.cpu:.2f} Damage: {self.damage_multiplier:.3f} Price: {isk(self.price)}\n"
        out += "\n".join(map(str, self.damage_mods))
        return out


@alru_cache(ttl=60)
async def get_abyssals_mutamarket(type_id: int, type_name: str):
    """Fetch all abyssals from a certain type from the mutamarket API"""
    url = f"https://mutamarket.com/api/modules/type/{type_id}/item-exchange/contracts-only/"
    item_data = await get(url)

    modules = []
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

        module = DamageMod(
            type_id=item.get("mutator_type_id"),
            type_name=type_name
        )

        module.add_stats_from_attributes(attributes)
        module.price = contract.get("price")

        module.add_unique_instance(
            module_id=item.get("id"),
            contract_id=contract.get("id")
        )

        modules.append(module)
    return modules


async def fetch_module_prices(modules):
    await asyncio.gather(*[m.fetch_price() for m in modules])


def module_combinations(repeatable_mods, unique_mods, count) -> Generator[list[Any] | list[DamageMod], Any, None]:
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


def should_filter_module(module: DamageMod, all_modules: list[DamageMod], max_price: float):
    """Helper function for filter_modules"""
    # Remove modules outside of max price
    if module.price > max_price:
        return True

    for other_module in all_modules:

        # Remove strictly worse modules
        if (module.cpu >= other_module.cpu and
                module.rof >= other_module.rof and
                module.damage <= other_module.damage and
                module.price > other_module.price):
            return True

    return False


def filter_modules(modules: list[DamageMod], max_price: float) -> list[DamageMod]:
    """filter out any modules that are strictly worse than some other modules"""

    modules_to_remove = [m for m in modules if should_filter_module(m, modules, max_price)]

    modules = list(set(modules) - set(modules_to_remove))

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
) -> Generator[tuple[DamageModSet, Any], Any, None]:
    """return the best module sets based on all possible module sets, as well as their relative grading"""
    sorting_points = []
    usable_sets = []

    for combination in module_combinations(repeatable_mods, unique_mods, count):

        damage_mod_set = DamageModSet(combination)

        if damage_mod_set.cpu >= max_cpu:
            continue  # Skip invalid sets early

        # Precompute expensive calculations
        price = float(damage_mod_set.price)
        damage_multiplier = float(damage_mod_set.get_damage_multiplier(**kwargs))

        sorting_points.append((price, damage_multiplier))

        if min_price < price < max_price:
            usable_sets.append((damage_mod_set, price, damage_multiplier))

    sorter = RelationalSorter(sorting_points)

    # Use heapq.nlargest instead of sorting everything
    best_sets = heapq.nlargest(
        results,
        usable_sets,
        key=lambda c: sorter((c[1], c[2]))  # Using precomputed values
    )

    for damage_mod_set, price, damage_multiplier in best_sets:
        yield damage_mod_set, sorter((price, damage_multiplier))


async def send_best(interaction, args, unique_mods, repeatable_mods):
    await interaction.response.defer()
    slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig = args

    # Parse human ISK prices e.g. 1b 1m 100kk
    min_price = convert(min_price)
    max_price = convert(max_price)

    # Default arguments
    count = count or 3
    uptime = uptime or 1.0
    rof_rig = rof_rig or ""
    damage_rig = damage_rig or ""

    # Filter modules
    unique_mods = filter_modules(unique_mods, max_price)
    repeatable_mods = filter_modules(repeatable_mods, max_price)

    # Return early if there are to many combinations
    total_combinations = (len(unique_mods) + len(repeatable_mods)) ** slots

    if total_combinations > 8e8:
        await interaction.followup.send(
            f"There are approximately {total_combinations} combinations - to many for the bot to handle!\n "
            "Consider reducing the price range or amount of slots.")
        return
    elif total_combinations > 1e8:
        await interaction.followup.send(
            f"This might take a while, there are approximately {total_combinations} combinations!")

    # Find sets
    loop = asyncio.get_running_loop()
    sets = await loop.run_in_executor(
        None, functools.partial(
            best_sets,
            unique_mods, repeatable_mods, slots, min_price, max_price, max_cpu, count,
            uptime=uptime, rof_rig=rof_rig, damage_rig=damage_rig
        )
    )

    # Make printout
    has_set = False
    for item_set, efficiency in sets:
        has_set = True
        await interaction.followup.send(f"Efficiency: {efficiency}\n {item_set}")

    if not has_set:
        await interaction.followup.send("No combinations found for these requirements!")


class DamageModCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ballistics",
        description="Get the best Ballistic Control System Set based on filters and pareto-optimization."
    )
    @app_commands.describe(
        slots="Number of module slots (e.g. 2, 3)",
        max_cpu="Maximum CPU available",
        min_price="Minimum ISK price",
        max_price="Maximum ISK price",
        uptime="Uptime percentage of guns without damage mods (optional)",
        count="Number of combinations to show (optional)",
        rof_rig="ROF rig type fitted (optional, e.g. t1, t2, t1x2)",
        damage_rig="Damage rig type fitted (optional, e.g. t1, t2, t1x2)"
    )
    @slash_command_error_handler
    async def ballistics(
            self,
            interaction: Interaction,
            slots: int,
            max_cpu: float,
            min_price: str,
            max_price: str,
            uptime: Optional[float] = None,
            count: Optional[int] = None,
            rof_rig: Optional[str] = None,
            damage_rig: Optional[str] = None
    ):
        args = (slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig)

        ballistics_unique = await get_abyssals_mutamarket(
            49738, "Abyssal Ballistics Control System"
        )

        ballistics_repeatable = [
            DamageMod(
                21484, "'Full Duplex' Ballistic Control System",
                cpu=22, damage=1.10, rof=0.9
            ),
            DamageMod(
                12274, "Ballistic Control System I",
                cpu=35, damage=1.07, rof=0.92
            ),
            DamageMod(
                16457, "Crosslink Compact Ballistic Control System",
                cpu=31, damage=1.08, rof=0.90
            ),
            DamageMod(
                22291, "Ballistic Control System II",
                cpu=40, damage=1.1, rof=0.90
            ),
            DamageMod(
                46270, "Kaatara's Custom Ballistic Control System",
                cpu=38, damage=1.1, rof=0.90
            ),
            DamageMod(
                15681, "Caldari Navy Ballistic Control System",
                cpu=24, damage=1.12, rof=0.89
            ),
            DamageMod(
                13935, "Domination Ballistic Control System",
                cpu=24, damage=1.12, rof=0.89
            ),
            DamageMod(
                13937, "Dread Guristas Ballistic Control System",
                cpu=24, damage=1.12, rof=0.89
            ),
            DamageMod(
                28563, "Khanid Navy Ballistic Control System",
                cpu=24, damage=1.12, rof=0.89
            ),
            DamageMod(
                15683, "Republic Fleet Ballistic Control System",
                cpu=24, damage=1.12, rof=0.89
            ),
        ]

        await fetch_module_prices(ballistics_repeatable)
        await send_best(interaction, args, ballistics_unique, ballistics_repeatable)

    @app_commands.command(
        name="entropics",
        description="Get the best Entropic Radiation Sink Set based on filters and pareto-optimization."
    )
    @app_commands.describe(
        slots="Number of module slots (e.g. 2, 3)",
        max_cpu="Maximum CPU available",
        min_price="Minimum ISK price",
        max_price="Maximum ISK price",
        uptime="Uptime percentage of guns without damage mods (optional)",
        count="Number of combinations to show (optional)",
        rof_rig="ROF rig type fitted (optional, e.g. t1, t2, t1x2)",
        damage_rig="Damage rig type fitted (optional, e.g. t1, t2, t1x2)"
    )
    @slash_command_error_handler
    async def entropics(
            self,
            interaction: Interaction,
            slots: int,
            max_cpu: float,
            min_price: str,
            max_price: str,
            uptime: Optional[float] = None,
            count: Optional[int] = None,
            rof_rig: Optional[str] = None,
            damage_rig: Optional[str] = None
    ):
        args = (slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig)

        entropics_unique = await get_abyssals_mutamarket(
            49734, "Abyssal Entropic Radiation Sink"
        )

        entropics_repeatable = [
            DamageMod(
                47908, "Entropic Radiation Sink I",
                cpu=27, damage=1.09, rof=0.96
            ),
            DamageMod(
                47909, "Compact Entropic Radiation Sink",
                cpu=25, damage=1.10, rof=0.95
            ),
            DamageMod(
                47911, "Entropic Radiation Sink II",
                cpu=30, damage=1.13, rof=0.94
            ),
            DamageMod(
                52244, "Veles Entropic Radiation Sink",
                cpu=23, damage=1.14, rof=0.93
            ),
        ]

        await fetch_module_prices(entropics_repeatable)
        await send_best(interaction, args, entropics_unique, entropics_repeatable)

    @app_commands.command(
        name="gyros",
        description="Get the best Gyrostabilizer Set based on filters and pareto-optimization."
    )
    @app_commands.describe(
        slots="Number of module slots (e.g. 2, 3)",
        max_cpu="Maximum CPU available",
        min_price="Minimum ISK price",
        max_price="Maximum ISK price",
        uptime="Uptime percentage of guns without damage mods (optional)",
        count="Number of combinations to show (optional)",
        rof_rig="ROF rig type fitted (optional, e.g. t1, t2, t1x2)",
        damage_rig="Damage rig type fitted (optional, e.g. t1, t2, t1x2)"
    )
    @slash_command_error_handler
    async def gyros(
            self,
            interaction: Interaction,
            slots: int,
            max_cpu: float,
            min_price: str,
            max_price: str,
            uptime: Optional[float] = None,
            count: Optional[int] = None,
            rof_rig: Optional[str] = None,
            damage_rig: Optional[str] = None
    ):
        args = (slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig)

        gyros_unique = await get_abyssals_mutamarket(
            49730, "Abyssal Gyrostabilizer"
        )

        gyros_repeatable = [
            DamageMod(
                518, "'Basic' Gyrostabilizer",
                cpu=16.0, damage=1.07, rof=0.93
            ),
            DamageMod(
                519, "Gyrostabilizer II",
                cpu=30.0, damage=1.10, rof=0.90
            ),
            DamageMod(
                520, "Gyrostabilizer I",
                cpu=27.0, damage=1.07, rof=0.92
            ),
            DamageMod(
                21486, "'Kindred' Gyrostabilizer",
                cpu=18.0, damage=1.10, rof=0.90,
            ),
            DamageMod(
                5933, "Counterbalanced Compact Gyrostabilizer",
                cpu=25.0, damage=1.08, rof=0.90,
            ),
            DamageMod(
                13939, "Domination Gyrostabilizer",
                cpu=20.0, damage=1.12, rof=0.89,
            ),
            DamageMod(
                15806, "Republic Fleet Gyrostabilizer",
                cpu=20.0, damage=1.12, rof=0.89,
            ),
        ]

        await fetch_module_prices(gyros_repeatable)
        await send_best(interaction, args, gyros_unique, gyros_repeatable)

    @app_commands.command(
        name="heatsinks",
        description="Get the best Heat Sink Set based on filters and pareto-optimization."
    )
    @app_commands.describe(
        slots="Number of module slots (e.g. 2, 3)",
        max_cpu="Maximum CPU available",
        min_price="Minimum ISK price",
        max_price="Maximum ISK price",
        uptime="Uptime percentage of guns without damage mods (optional)",
        count="Number of combinations to show (optional)",
        rof_rig="ROF rig type fitted (optional, e.g. t1, t2, t1x2)",
        damage_rig="Damage rig type fitted (optional, e.g. t1, t2, t1x2)"
    )
    @slash_command_error_handler
    async def heatsinks(
            self,
            interaction: Interaction,
            slots: int,
            max_cpu: float,
            min_price: str,
            max_price: str,
            uptime: Optional[float] = None,
            count: Optional[int] = None,
            rof_rig: Optional[str] = None,
            damage_rig: Optional[str] = None
    ):
        args = (slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig)

        heatsinks_unique = await get_abyssals_mutamarket(
            49726, "Abyssal Heat Sink"
        )

        heatsinks_repeatable = [
            DamageMod(
                2363, "Heat Sink I",
                cpu=35.0, damage=1.07, rof=0.92
            ),
            DamageMod(
                5849, "Extruded Compact Heat Sink",
                cpu=25.0, damage=1.08, rof=0.90
            ),
            DamageMod(
                2364, "Heat Sink II",
                cpu=30.0, damage=1.1, rof=0.90
            ),
            DamageMod(
                1893, "'Basic' Heat Sink",
                cpu=16.0, damage=1.07, rof=0.93
            ),
            DamageMod(
                23902, "'Trebuchet' Heat Sink I",
                cpu=18.0, damage=1.1, rof=0.9
            ),
            DamageMod(
                44111, "Tahron's Custom Heat Sink",
                cpu=29.0, damage=1.1, rof=0.9,
            ),
            DamageMod(
                15810, "Imperial Navy Heat Sink",
                cpu=20.0, damage=1.12, rof=0.89
            ),
            DamageMod(
                13943, "True Sansha Heat Sink",
                cpu=20.0, damage=1.12, rof=0.89
            ),
            DamageMod(
                15808, "Ammatar Navy Heat Sink",
                cpu=20.0, damage=1.12, rof=0.89
            ),
        ]

        await fetch_module_prices(heatsinks_repeatable)
        await send_best(interaction, args, heatsinks_unique, heatsinks_repeatable)

    @app_commands.command(
        name="magstabs",
        description="Get the best Magnetic Field Stabilizer Set based on filters and pareto-optimization."
    )
    @app_commands.describe(
        slots="Number of module slots (e.g. 2, 3)",
        max_cpu="Maximum CPU available",
        min_price="Minimum ISK price",
        max_price="Maximum ISK price",
        uptime="Uptime percentage of guns without damage mods (optional)",
        count="Number of combinations to show (optional)",
        rof_rig="ROF rig type fitted (optional, e.g. t1, t2, t1x2)",
        damage_rig="Damage rig type fitted (optional, e.g. t1, t2, t1x2)"
    )
    @slash_command_error_handler
    async def magstabs(
            self,
            interaction: Interaction,
            slots: int,
            max_cpu: float,
            min_price: str,
            max_price: str,
            uptime: Optional[float] = None,
            count: Optional[int] = None,
            rof_rig: Optional[str] = None,
            damage_rig: Optional[str] = None
    ):
        args = (slots, max_cpu, min_price, max_price, uptime, count, rof_rig, damage_rig)

        magstabs_unique = await get_abyssals_mutamarket(
            49722, "Abyssal Magnetic Field Stabilizer"
        )

        magstabs_repeatable = [
            DamageMod(
                9944, "Magnetic Field Stabilizer I",
                cpu=35.0, damage=1.07, rof=0.92,
            ),
            DamageMod(
                10190, "Magnetic Field Stabilizer II",
                cpu=30.0, damage=1.10, rof=0.90,
            ),
            DamageMod(
                10188, "'Basic' Magnetic Field Stabilizer",
                cpu=16.0, damage=1.07, rof=0.93,
            ),
            DamageMod(
                22919, "'Monopoly' Magnetic Field Stabilizer",
                cpu=18.0, damage=1.10, rof=0.90,
            ),
            DamageMod(
                44113, "Kaatara's Custom Magnetic Field Stabilizer",
                cpu=29.0, damage=1.10, rof=0.90,
            ),
            DamageMod(
                44114, "Torelle's Custom Magnetic Field Stabilizer",
                cpu=29.0, damage=1.10, rof=0.90,
            ),
            DamageMod(
                15416, "Naiyon's Modified Magnetic Field Stabilizer",
                cpu=24.0, damage=1.14, rof=0.90,
            ),
            DamageMod(
                15895, "Federation Navy Magnetic Field Stabilizer",
                cpu=20.0, damage=1.12, rof=0.89,
            ),
            DamageMod(
                13945, "Shadow Serpentis Magnetic Field Stabilizer",
                cpu=20.0, damage=1.12, rof=0.89,
            ),
        ]

        await fetch_module_prices(magstabs_repeatable)
        await send_best(interaction, args, magstabs_unique, magstabs_repeatable)


async def setup(bot):
    await bot.add_cog(DamageModCog(bot))
