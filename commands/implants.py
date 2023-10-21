import asyncio
import itertools

import aiohttp
from async_lru import alru_cache

from utils import RelationalSorter, get_item_attributes
from utils import get_item_name, get_item_price
from utils import isk, convert


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
            return "**No stat increase for 0 isk (*infinite value!*)**\n"
        return f"**{self.bonus:.4} stat increase for {isk(self.price)} ** ({isk(self.price / (self.bonus - 1) / 100)} per %):\n" \
               f"{''.join(str(i) for i in self.implants)}"


def combinations(implants):
    """returns every possible combination of implants while
    factoring in their slots, as well as the option to not have any implant in a slot"""
    slot_dict = {x: [Implant(slot=x)] for x in range(1, 11)}  # Add in empty modules
    for implant in implants:
        slot_dict[implant.slot].append(implant)

    for x in itertools.product(*slot_dict.values()):
        yield ImplantSet(x)


async def implant_from_id(session, type_id, set_bonus_id=None, set_malus_id=None, set_multiplier_id=None,
                          bonus_ids=None, malus_ids=None):
    name = await get_item_name(type_id, session)
    price = await get_item_price(type_id, session)
    attributes = await get_item_attributes(type_id, session)
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


async def send_best(arguments, message, implants, command):
    if "help" in arguments:
        await message.channel.send(
            f"Usage:\n !{command} <min_price> <max_price>")
        return

    if "count" in arguments:
        count = int(arguments["count"][0])
    elif "c" in arguments:
        count = int(arguments["c"][0])
    else:
        count = 3

    sorter = RelationalSorter([(c.price, c.bonus) for c in combinations(implants)])
    filtered_combinations = [x for x in combinations(implants) if
                             convert(arguments[""][0]) <= x.price <= convert(arguments[""][1])]
    ret = "\n".join(
        map(str, sorted(filtered_combinations, key=lambda x: sorter((x.price, x.bonus)), reverse=True)[:count]))

    if ret == "":
        ret = "No implant sets found for that price range! \n Make sure you give the price in ISK, you can use k / m / b as modifiers for thousands / millions / billions."

    await message.channel.send(ret)


async def command_amulets(arguments, message):
    await send_best(arguments, message, await amulets(), "amulets")


@alru_cache(ttl=1800)
async def amulets():
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


async def command_ascendancies(arguments, message):
    await send_best(arguments, message, await ascendancies(), "ascendancies")


@alru_cache(ttl=1800)
async def ascendancies():
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


async def command_asklepians(arguments, message):
    await send_best(arguments, message, await asklepians(), "asklepians")


@alru_cache(ttl=1800)
async def asklepians():
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


async def command_crystals(arguments, message):
    await send_best(arguments, message, await crystals(), "crystals")


@alru_cache(ttl=1800)
async def crystals():
    return await implants_from_ids(
        [
            33923, 33924, 33927, 33925, 33926, 33928,  # LG Crystal
            22107, 22108, 22111, 22109, 22110, 22112,  # MG Crystal
            20121, 20157, 20158, 20159, 20160, 20161,  # HG Crystal
        ],
        set_bonus_id=548,
        set_multiplier_id=838,
    )


async def command_snakes(arguments, message):
    await send_best(arguments, message, await snakes(), "snakes")


@alru_cache(ttl=1800)
async def snakes():
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


async def command_talismans(arguments, message):
    await send_best(arguments, message, await talismans(), "talismans")


@alru_cache(ttl=1800)
async def talismans():
    return await implants_from_ids(
        [
            33965, 33966, 33969, 33967, 33968, 33970,  # LG
            22131, 22133, 22136, 22134, 22135, 22137,  # MG
            19534, 19535, 19536, 19537, 19538, 19539,  # HG
        ],
        set_malus_id=66,
        set_multiplier_id=799,
    )


async def command_halos(arguments, message):
    await send_best(arguments, message, await halos(), "halos")


@alru_cache(ttl=1800)
async def halos():
    return await implants_from_ids(
        [
            33935, 33936, 33939, 33937, 33938, 33940,  # LG
            22113, 22117, 22136, 22115, 22116, 22118,  # MG
            20498, 20500, 20506, 20502, 20504, 20508,  # HG
        ],
        set_malus_id=554,
        set_multiplier_id=863,
    )


async def command_hydras(arguments, message):
    await send_best(arguments, message, await halos(), "hydras")


@alru_cache(ttl=1800)
async def hydras():
    return await implants_from_ids(
        [
            54409, 54408, 54407, 54406, 54405, 54404,  # LG
            54403, 54402, 54401, 54400, 54399, 54398,  # MG
            54397, 54396, 54395, 54394, 54393, 54392,  # HG
        ],
        set_bonus_id=3031,  # There are other bonuses 3028 - 3030, but they are all the same
        set_multiplier_id=3027,
    )


async def command_mimesiss(arguments, message):
    await send_best(arguments, message, await halos(), "mimesiss")


@alru_cache(ttl=1800)
async def mimesiss():
    return await implants_from_ids(
        [
            52683, 52682, 52681, 52680, 52679, 52674,  # LG
            52790, 52789, 52788, 52787, 52786, 52785,  # MG
            52922, 52921, 52920, 52919, 52918, 52917,  # HG
        ],
        set_bonus_id=2023,  # Only look at max damage modifier
        set_multiplier_id=2825,
    )


async def command_raptures(arguments, message):
    await send_best(arguments, message, await halos(), "raptures")


@alru_cache(ttl=1800)
async def raptures():
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


async def command_saviors(arguments, message):
    await send_best(arguments, message, await halos(), "saviors")


@alru_cache(ttl=1800)
async def saviors():
    return await implants_from_ids(
        [
            53907, 53906, 53905, 53904, 53903, 53902,  # LG
            53901, 53900, 53899, 53898, 53897, 53896,  # MG
            53894, 53893, 53892, 53891, 53890, 53895,  # HG
        ],
        set_malus_id=3024,
        set_multiplier_id=3023,
    )


async def command_harvests(arguments, message):
    await send_best(arguments, message, await halos(), "harvests")


@alru_cache(ttl=1800)
async def harvests():
    return await implants_from_ids(
        [
            33946, 33945, 33944, 33943, 33942, 33941,  # LG
            28807, 28806, 28805, 28804, 28803, 28802,  # MG
        ],
        set_bonus_id=351,
        set_multiplier_id=1219,
    )


async def command_nomads(arguments, message):
    await send_best(arguments, message, await halos(), "nomads")


@alru_cache(ttl=1800)
async def nomads():
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


async def command_virtues(arguments, message):
    await send_best(arguments, message, await halos(), "command_virtues")


@alru_cache(ttl=1800)
async def command_virtues():
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
