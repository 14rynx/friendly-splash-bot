import asyncio
import itertools

import aiohttp
from async_lru import alru_cache
from discord.ext import commands

from network import get_item_name, get_item_price, get_dogma_attributes
from utils import RelationalSorter, unix_style_arg_parser, convert, command_error_handler, isk


class Implant:
    """Holds all the numbers for one implant."""

    def __init__(self, type_id=0, name="", price=0, slot=1, set_bonus=0.0, set_multiplier=1.0, bonus=0.0):
        self.name = name
        self.slot = slot
        self.type_id = type_id
        self.set_bonus = set_bonus
        self.set_multiplier = set_multiplier
        self.bonus = bonus
        self.price = price

    def __str__(self):
        if self.name == "":
            return ""
        else:
            return self.name + "\n"


class ImplantSet:
    """Holds all the numbers for a set of implants which affect the same attribute."""

    def __init__(self, implants):
        self.implants = implants
        self.relational_efficiency = 0

    @property
    def bonus(self):
        multiplier = 1
        for implant in self.implants:
            multiplier *= implant.set_multiplier

        bonus = 1
        for implant in self.implants:
            bonus *= (1 + implant.bonus * 0.01) * (1 + implant.set_bonus * 0.01 * multiplier)
        return bonus

    @property
    def price(self):
        return sum(implant.price for implant in self.implants)

    def __str__(self):
        if self.bonus == 1:
            return "**No stat increase for 0 isk ** (*infinite value!*)\n"
        return f"**{self.bonus:.4} stat increase for {isk(self.price)} ** ({isk(self.price / (self.bonus - 1) / 100)} per %):\n" \
               f"{''.join(str(i) for i in self.implants)}"

    def str_with_efficiency(self, efficiency=1.0):
        if self.bonus == 1:
            return f"**No stat increase for 0 isk ** (*infinite value!*) (Efficiency: {efficiency})\n"
        return f"**{self.bonus:.4} stat increase for {isk(self.price)} ** ({isk(self.price / (self.bonus - 1) / 100)} per %) (Efficiency: {efficiency}):\n" \
               f"{''.join(str(i) for i in self.implants)}"


async def implant_from_id(session, type_id, set_bonus_id=None, set_malus_id=None, set_multiplier_id=None,
                          bonus_ids=None, malus_ids=None):
    name = await get_item_name(type_id)
    price = await get_item_price(type_id)
    attributes = await get_dogma_attributes(type_id)
    slot = int(attributes.get(331))

    if set_multiplier_id in attributes:  # The implant is part of a set
        if set_bonus_id:
            set_bonus = float(attributes.get(set_bonus_id, 0))
        elif set_malus_id:
            set_bonus = 100 / (1 + float(attributes.get(set_malus_id, 0)) * 0.01) - 100  # Convert to Bonus scale
        else:
            raise ValueError("Bonus / Malus id for Implant Set not correct!")
        set_multiplier = float(attributes.get(set_multiplier_id, 0))
        return Implant(type_id, name, price, slot, set_bonus=set_bonus, set_multiplier=set_multiplier)

    else:  # The Implant is not part of a set
        bonus = None
        if bonus_ids:
            for bonus_id in bonus_ids:
                if bonus_id in attributes:
                    bonus = float(attributes[bonus_id])
        if malus_ids:
            for malus_id in malus_ids:
                if malus_id in attributes:
                    bonus = 100 / (1 + float(attributes[malus_id]) * 0.01) - 100  # Convert to Bonus scale
        if not bonus:
            raise ValueError("Bonus / Malus id for Hardwiring not correct!")
        return Implant(type_id, name, price, slot, bonus=bonus)


async def implants_from_ids(type_ids, set_bonus_id=None, set_malus_id=None, set_multiplier_id=None, bonus_ids=None,
                            malus_ids=None):
    async with aiohttp.ClientSession() as session:
        tasks = [
            implant_from_id(session, type_id, set_bonus_id, set_malus_id, set_multiplier_id, bonus_ids, malus_ids)
            for type_id in type_ids
        ]
        implants = await asyncio.gather(*tasks)
        return implants


def combinations(implants):
    """returns every possible combination of implants while
    factoring in their slots, as well as the option to not have any implant in a slot"""
    slot_dict = {x: [Implant(slot=x)] for x in range(1, 11)}  # Add in empty modules
    for implant in implants:
        slot_dict[implant.slot].append(implant)

    for x in itertools.product(*slot_dict.values()):
        yield ImplantSet(x)


async def send_best(ctx, min_price, max_price, implants):
    arguments = unix_style_arg_parser(min_price, max_price)

    if "help" in arguments:
        await ctx.send(
            f"")
        return

    sorter = RelationalSorter([(c.price, c.bonus) for c in combinations(implants)])
    filtered_combinations = [x for x in combinations(implants) if convert(min_price) <= x.price <= convert(max_price)]

    best_sets = sorted(filtered_combinations, key=lambda x: sorter((x.price, x.bonus)), reverse=True)[:3]
    ret = "\n".join([x.str_with_efficiency(sorter((x.price, x.bonus))) for x in best_sets])

    if ret == "":
        ret = "No implant sets found for that price range! \n Make sure you give the price in ISK, you can use k / m / b as modifiers for thousands / millions / billions."

    await ctx.send(ret)


@alru_cache(ttl=1800)
async def _amulets():
    return await implants_from_ids(
        [
            33953, 33954, 33957, 33955, 33956, 33958,  # LG Amulet
            22119, 22120, 22123, 22121, 22122, 22124,  # MG Amulet
            20499, 20501, 20507, 20503, 20505, 20509,  # HG Amulet
            27074, 3479, 13256, 3481, 19550, 3482, 21606,  # HG-100x
            32254,  # Imperial Navy Modified 'Noble' Implant
        ],
        set_bonus_id=335,
        set_multiplier_id=864,
        bonus_ids=[1083],
    )


@alru_cache(ttl=1800)
async def _ascendancies():
    return await implants_from_ids(
        [
            33555, 33557, 33563, 33559, 33561, 33565,  # MG Ascendancy
            33516, 33525, 33528, 33526, 33527, 33529,  # HG Ascendancy
            27115, 3117, 13242, 3118, 27114, 3119,  # WS-6xx
        ],
        set_bonus_id=624,
        set_multiplier_id=1932,
        bonus_ids=[624],
    )


@alru_cache(ttl=1800)
async def _asklepians():
    return await implants_from_ids(
        [
            42145, 42146, 42202, 42200, 42201, 42203,  # LG Asklepian
            42204, 42205, 42206, 42207, 42208, 42209,  # MG Asklepian
            42210, 42211, 42212, 42213, 42214, 42215,  # HG Asklepian
            27070, 3291, 13258, 3292, 19547, 3299,  # RS-60x
            20358,  # Numon Family Heirloom
            27073, 3476, 19684, 3477, 19685, 3478,  # RP-90x
            32254,  # Imperial Navy Modified 'Noble' Implant
        ],
        set_bonus_id=2457,
        set_multiplier_id=803,
        bonus_ids=[806],
        malus_ids=[312],
    )


@alru_cache(ttl=1800)
async def _crystals():
    return await implants_from_ids(
        [
            33923, 33924, 33927, 33925, 33926, 33928,  # LG Crystal
            22107, 22108, 22111, 22109, 22110, 22112,  # MG Crystal
            20121, 20157, 20158, 20159, 20160, 20161,  # HG Crystal
        ],
        set_bonus_id=548,
        set_multiplier_id=838,
    )


@alru_cache(ttl=1800)
async def _snakes():
    return await implants_from_ids(
        [
            33959, 33960, 33963, 33961, 33962, 33964,  # LG Snake
            22125, 22126, 22129, 22127, 22128, 22130,  # MG Snake
            19540, 19551, 19553, 19554, 19555, 19556,  # HG Snake
            27097, 3096, 13237, 3097, 16003, 3100, 24669,  # NN-60x
            24663,  # Zor's Custom Navigation Hyperlink
        ],
        set_bonus_id=315,
        set_multiplier_id=802,
        bonus_ids=[1076, 318],
    )


@alru_cache(ttl=1800)
async def _talismans():
    return await implants_from_ids(
        [
            33965, 33966, 33969, 33967, 33968, 33970,  # LG
            22131, 22133, 22136, 22134, 22135, 22137,  # MG
            19534, 19535, 19536, 19537, 19538, 19539,  # HG
        ],
        set_malus_id=66,
        set_multiplier_id=799,
    )


@alru_cache(ttl=1800)
async def _halos():
    return await implants_from_ids(
        [
            33935, 33936, 33939, 33937, 33938, 33940,  # LG
            22113, 22114, 22117, 22115, 22116, 22118,  # MG
            20498, 20500, 20506, 20502, 20504, 20508,  # HG
        ],
        set_malus_id=554,
        set_multiplier_id=863,
    )


@alru_cache(ttl=1800)
async def _hydras():
    return await implants_from_ids(
        [
            54409, 54408, 54407, 54406, 54405, 54404,  # LG
            54403, 54402, 54401, 54400, 54399, 54398,  # MG
            54397, 54396, 54395, 54394, 54393, 54392,  # HG
        ],
        set_bonus_id=3031,  # There are other bonuses 3028 - 3030, but they are all the same
        set_multiplier_id=3027,
    )


@alru_cache(ttl=1800)
async def _mimesiss():
    return await implants_from_ids(
        [
            52683, 52682, 52681, 52680, 52679, 52674,  # LG
            52790, 52789, 52788, 52787, 52786, 52785,  # MG
            52922, 52921, 52920, 52919, 52918, 52917,  # HG
        ],
        set_bonus_id=2023,  # Only look at max damage modifier
        set_multiplier_id=2825,
    )


@alru_cache(ttl=1800)
async def _raptures():
    return await implants_from_ids(
        [
            57116, 57114, 57113, 57112, 57111, 57110,  # LG
            57122, 57121, 57120, 57119, 57118, 57117,  # MG
            57128, 57127, 57126, 57125, 57124, 57123,  # HG
            27119, 3240, 13260, 3241, 27118, 3246,  # EO-60x
            27117, 3237, 13259, 3238, 27116, 3239,  # EM-80x
        ],
        set_malus_id=314,
        set_multiplier_id=3107,
        bonus_ids=[1079],
        malus_ids=[314],
    )


@alru_cache(ttl=1800)
async def _saviors():
    return await implants_from_ids(
        [
            53907, 53906, 53905, 53904, 53903, 53902,  # LG
            53901, 53900, 53899, 53898, 53897, 53896,  # MG
            53894, 53893, 53892, 53891, 53890, 53895,  # HG
        ],
        set_malus_id=3024,
        set_multiplier_id=3023,
    )


@alru_cache(ttl=1800)
async def _harvests():
    return await implants_from_ids(
        [
            33946, 33945, 33944, 33943, 33942, 33941,  # LG
            28807, 28806, 28805, 28804, 28803, 28802,  # MG
        ],
        set_bonus_id=351,
        set_multiplier_id=1219,
    )


@alru_cache(ttl=1800)
async def _nirvanas():
    return await implants_from_ids(
        [
            53853, 53854, 53855, 53856, 53857, 53839,  # LG
            53704, 53705, 53708, 53706, 53707, 53709,  # MG
            53710, 53711, 53715, 53712, 53713, 53714,  # MG
            27105, 3080, 10228, 3081, 16246, 3084  # SM-70x
        ],
        set_bonus_id=3015,
        set_multiplier_id=3017,
        bonus_ids=[337]
    )


@alru_cache(ttl=1800)
async def _nomads():
    return await implants_from_ids(
        [
            33952, 33951, 33950, 33949, 33948, 33947,  # LG
            28801, 28800, 28799, 28798, 28797, 28796,  # MG
            27099, 3093, 13240, 3094, 16004, 3095  # EM-70x
        ],
        set_malus_id=151,
        set_multiplier_id=1282,
        malus_ids=[151]
    )


@alru_cache(ttl=1800)
async def _virtues():
    return await implants_from_ids(
        [
            33976, 33975, 33974, 33973, 33972, 33971,  # LG
            28813, 28812, 28811, 28810, 28809, 28808,  # MG
            27195, 27188, 27194,  # AR-8xx
        ],
        set_bonus_id=846,
        set_multiplier_id=1284,
        bonus_ids=[846]
    )


@commands.command()
@command_error_handler
async def ascendancies(ctx, min_price, max_price):
    """
    !ascendancies <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _ascendancies())


@commands.command()
@command_error_handler
async def asklepians(ctx, min_price, max_price):
    """
    !asklepians <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _asklepians())


@commands.command()
@command_error_handler
async def amulets(ctx, min_price, max_price):
    """
    !amulets <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _amulets())


@commands.command()
@command_error_handler
async def crystals(ctx, min_price, max_price):
    """
    !crystals <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _crystals())


@commands.command()
@command_error_handler
async def talismans(ctx, min_price, max_price):
    """
    !talismans <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _talismans())


@commands.command()
@command_error_handler
async def snakes(ctx, min_price, max_price):
    """
    !snakes <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _snakes())


@commands.command()
@command_error_handler
async def halos(ctx, min_price, max_price):
    """
    !halos <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _halos())


@commands.command()
@command_error_handler
async def hydras(ctx, min_price, max_price):
    """
    !hydras <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _hydras())


@commands.command()
@command_error_handler
async def mimesiss(ctx, min_price, max_price):
    """
    !mimesiss <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _mimesiss())


@commands.command()
@command_error_handler
async def raptures(ctx, min_price, max_price):
    """
    !raptures <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _raptures())


@commands.command()
@command_error_handler
async def saviors(ctx, min_price, max_price):
    """
    !saviors <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _saviors())


@commands.command()
@command_error_handler
async def harvests(ctx, min_price, max_price):
    """
    !harvests <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _harvests())


@commands.command()
@command_error_handler
async def nirvanas(ctx, min_price, max_price):
    """
    !nirvanas <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _nirvanas())


@commands.command()
@command_error_handler
async def nomads(ctx, min_price, max_price):
    """
    !nomads <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _nomads())


@commands.command()
@command_error_handler
async def virtues(ctx, min_price, max_price):
    """
    !virtues <min_price> <max_price>
    """
    await send_best(ctx, min_price, max_price, await _virtues())


async def setup(bot):
    bot.add_command(ascendancies)
    bot.add_command(asklepians)
    bot.add_command(amulets)
    bot.add_command(crystals)
    bot.add_command(talismans)
    bot.add_command(snakes)
    bot.add_command(halos)
    bot.add_command(hydras)
    bot.add_command(mimesiss)
    bot.add_command(raptures)
    bot.add_command(saviors)
    bot.add_command(harvests)
    bot.add_command(nirvanas)
    bot.add_command(nomads)
    bot.add_command(virtues)
