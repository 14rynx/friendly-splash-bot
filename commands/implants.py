import itertools

import aiohttp
from async_lru import alru_cache

from utils import RelationalSorter
from utils import get_item_name, get_item_price
from utils import isk, convert


class Implant:
    def __init__(self, id=0, name="", price=0, slot=1, set_bonus=0.0, set_multiplier=1.0, bonus=0.0):
        self.name = name
        self.slot = slot
        self.id = id
        self.set_bonus = set_bonus
        self.set_multiplier = set_multiplier
        self.bonus = bonus
        self.price = price

    def __str__(self):
        return self.name


class ImplantSet:
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
        newline = "\n"
        return f"**{self.bonus:.4} stat increase for {isk(self.price)} ** ({isk(self.price / (self.bonus - 1) / 100)} per %)" \
               f"{newline}{newline.join(str(i) for i in self.implants)}"


def combinations(implants):
    slot_dict = {}
    for implant in implants:
        if implant.slot in slot_dict:
            slot_dict[implant.slot].append(implant)
        else:
            slot_dict.update({implant.slot: [implant]})

    total = 1
    for key, value in slot_dict.items():
        total *= len(value)

    for x in itertools.product(*slot_dict.values()):
        yield ImplantSet(x)


async def get_data(type_id):
    async with aiohttp.ClientSession() as session:
        name = await get_item_name(type_id, session)
        price = await get_item_price(type_id, session)
        return type_id, name, price


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
    await message.channel.send(ret)


@alru_cache(ttl=1800)
async def amulets():
    return [
        # LG Amulet
        Implant(*(await get_data(33953)), 1, set_bonus=1, set_multiplier=1.02),
        Implant(*(await get_data(33954)), 2, set_bonus=2, set_multiplier=1.02),
        Implant(*(await get_data(33957)), 3, set_bonus=3, set_multiplier=1.02),
        Implant(*(await get_data(33955)), 4, set_bonus=4, set_multiplier=1.02),
        Implant(*(await get_data(33956)), 5, set_bonus=5, set_multiplier=1.02),
        Implant(*(await get_data(33958)), 6, set_bonus=0, set_multiplier=1.1),

        # MG Amulet
        Implant(*(await get_data(22119)), 1, set_bonus=1, set_multiplier=1.1),
        Implant(*(await get_data(22120)), 2, set_bonus=2, set_multiplier=1.1),
        Implant(*(await get_data(22123)), 3, set_bonus=3, set_multiplier=1.1),
        Implant(*(await get_data(22121)), 4, set_bonus=4, set_multiplier=1.1),
        Implant(*(await get_data(22122)), 5, set_bonus=5, set_multiplier=1.1),
        Implant(*(await get_data(22124)), 6, set_bonus=0, set_multiplier=1.25),

        # HG Amulet
        Implant(*(await get_data(20499)), 1, set_bonus=1, set_multiplier=1.15),
        Implant(*(await get_data(20501)), 2, set_bonus=2, set_multiplier=1.15),
        Implant(*(await get_data(20507)), 3, set_bonus=3, set_multiplier=1.15),
        Implant(*(await get_data(20503)), 4, set_bonus=4, set_multiplier=1.15),
        Implant(*(await get_data(20505)), 5, set_bonus=5, set_multiplier=1.15),
        Implant(*(await get_data(20509)), 6, set_bonus=0, set_multiplier=1.5),

        # Noble Hull Upgrades
        Implant(*(await get_data(27074)), 10, bonus=1),
        Implant(*(await get_data(3479)), 10, bonus=2),
        Implant(*(await get_data(13256)), 10, bonus=3),
        Implant(*(await get_data(3481)), 10, bonus=4),
        Implant(*(await get_data(19550)), 10, bonus=5),
        Implant(*(await get_data(3482)), 10, bonus=6),
        Implant(*(await get_data(21606)), 10, bonus=8),

        # Imp Navy Noble
        Implant(*(await get_data(32254)), 10, bonus=3),
    ]


@alru_cache(ttl=1800)
async def ascendancies():
    return [
        # MG Ascendancy
        Implant(*(await get_data(33555)), 1, set_bonus=1, set_multiplier=1.1),
        Implant(*(await get_data(33557)), 2, set_bonus=2, set_multiplier=1.1),
        Implant(*(await get_data(33563)), 3, set_bonus=3, set_multiplier=1.1),
        Implant(*(await get_data(33559)), 4, set_bonus=4, set_multiplier=1.1),
        Implant(*(await get_data(33561)), 5, set_bonus=5, set_multiplier=1.1),
        Implant(*(await get_data(33565)), 6, set_bonus=0, set_multiplier=1.35),

        # HG Ascendancy
        Implant(*(await get_data(33516)), 1, set_bonus=1, set_multiplier=1.15),
        Implant(*(await get_data(33525)), 2, set_bonus=2, set_multiplier=1.15),
        Implant(*(await get_data(33528)), 3, set_bonus=3, set_multiplier=1.15),
        Implant(*(await get_data(33526)), 4, set_bonus=4, set_multiplier=1.15),
        Implant(*(await get_data(33527)), 5, set_bonus=5, set_multiplier=1.15),
        Implant(*(await get_data(33529)), 6, set_bonus=0, set_multiplier=1.7),

        # Warpspeed Hardwirings
        Implant(*(await get_data(27115)), 6, bonus=5),
        Implant(*(await get_data(3117)), 6, bonus=8),
        Implant(*(await get_data(13242)), 6, bonus=10),
        Implant(*(await get_data(3118)), 6, bonus=13),
        Implant(*(await get_data(27114)), 6, bonus=15),
        Implant(*(await get_data(3119)), 6, bonus=18),
    ]


@alru_cache(ttl=1800)
async def asklepians():
    return [
        # LG Asklepian
        Implant(*(await get_data(42145)), 1, set_bonus=1, set_multiplier=1.02),
        Implant(*(await get_data(42146)), 2, set_bonus=2, set_multiplier=1.02),
        Implant(*(await get_data(42202)), 3, set_bonus=3, set_multiplier=1.02),
        Implant(*(await get_data(42200)), 4, set_bonus=4, set_multiplier=1.02),
        Implant(*(await get_data(42201)), 5, set_bonus=5, set_multiplier=1.02),
        Implant(*(await get_data(42203)), 6, set_bonus=0, set_multiplier=1.1),

        # MG Asklepian
        Implant(*(await get_data(42204)), 1, set_bonus=1, set_multiplier=1.1),
        Implant(*(await get_data(42205)), 2, set_bonus=2, set_multiplier=1.1),
        Implant(*(await get_data(42206)), 3, set_bonus=3, set_multiplier=1.1),
        Implant(*(await get_data(42207)), 4, set_bonus=4, set_multiplier=1.1),
        Implant(*(await get_data(42208)), 5, set_bonus=5, set_multiplier=1.1),
        Implant(*(await get_data(42209)), 6, set_bonus=0, set_multiplier=1.25),

        # HG Asklepian
        Implant(*(await get_data(42210)), 1, set_bonus=1, set_multiplier=1.15),
        Implant(*(await get_data(42211)), 2, set_bonus=2, set_multiplier=1.15),
        Implant(*(await get_data(42212)), 3, set_bonus=3, set_multiplier=1.15),
        Implant(*(await get_data(42213)), 4, set_bonus=4, set_multiplier=1.15),
        Implant(*(await get_data(42214)), 5, set_bonus=5, set_multiplier=1.15),
        Implant(*(await get_data(42215)), 6, set_bonus=0, set_multiplier=1.5),

        # Noble Repair Systems
        Implant(*(await get_data(27070)), 6, bonus=1.0101),
        Implant(*(await get_data(3291)), 6, bonus=2.0202),
        Implant(*(await get_data(13258)), 6, bonus=3.0303),
        Implant(*(await get_data(3292)), 6, bonus=4.0404),
        Implant(*(await get_data(19547)), 6, bonus=5.0505),
        Implant(*(await get_data(3299)), 6, bonus=6.0606),
        Implant(*(await get_data(20358)), 6, bonus=7.0707),

        # Noble Repair Systems
        Implant(*(await get_data(27073)), 9, bonus=1),
        Implant(*(await get_data(3476)), 9, bonus=2),
        Implant(*(await get_data(19684)), 9, bonus=3),
        Implant(*(await get_data(3477)), 9, bonus=4),
        Implant(*(await get_data(19685)), 9, bonus=5),
        Implant(*(await get_data(3478)), 9, bonus=6),

        Implant(*(await get_data(32254)), 10, bonus=3)
    ]


@alru_cache(ttl=1800)
async def crystals():
    return [
        # LG Crystal
        Implant(*(await get_data(33923)), 1, set_bonus=1, set_multiplier=1.02),
        Implant(*(await get_data(33924)), 2, set_bonus=2, set_multiplier=1.02),
        Implant(*(await get_data(33927)), 3, set_bonus=3, set_multiplier=1.02),
        Implant(*(await get_data(33925)), 4, set_bonus=4, set_multiplier=1.02),
        Implant(*(await get_data(33926)), 5, set_bonus=5, set_multiplier=1.02),
        Implant(*(await get_data(33928)), 6, set_bonus=0, set_multiplier=1.1),

        # MG Crystal
        Implant(*(await get_data(22107)), 1, set_bonus=1, set_multiplier=1.1),
        Implant(*(await get_data(22108)), 2, set_bonus=2, set_multiplier=1.1),
        Implant(*(await get_data(22111)), 3, set_bonus=3, set_multiplier=1.1),
        Implant(*(await get_data(22109)), 4, set_bonus=4, set_multiplier=1.1),
        Implant(*(await get_data(22110)), 5, set_bonus=5, set_multiplier=1.1),
        Implant(*(await get_data(22112)), 6, set_bonus=0, set_multiplier=1.25),

        # HG Crystal
        Implant(*(await get_data(20121)), 1, set_bonus=1, set_multiplier=1.15),
        Implant(*(await get_data(20157)), 2, set_bonus=2, set_multiplier=1.15),
        Implant(*(await get_data(20158)), 3, set_bonus=3, set_multiplier=1.15),
        Implant(*(await get_data(20159)), 4, set_bonus=4, set_multiplier=1.15),
        Implant(*(await get_data(20160)), 5, set_bonus=5, set_multiplier=1.15),
        Implant(*(await get_data(20161)), 6, set_bonus=0, set_multiplier=1.5)
    ]


@alru_cache(ttl=1800)
async def snakes():
    return [
        # LG Snake
        Implant(*(await get_data(33959)), 1, set_bonus=0.5, set_multiplier=1.05),
        Implant(*(await get_data(33960)), 2, set_bonus=0.62, set_multiplier=1.05),
        Implant(*(await get_data(33963)), 3, set_bonus=0.75, set_multiplier=1.05),
        Implant(*(await get_data(33961)), 4, set_bonus=0.88, set_multiplier=1.05),
        Implant(*(await get_data(33962)), 5, set_bonus=1, set_multiplier=1.05),
        Implant(*(await get_data(33964)), 6, set_bonus=0, set_multiplier=2.1),

        # MG Snake
        Implant(*(await get_data(22125)), 1, set_bonus=0.5, set_multiplier=1.1),
        Implant(*(await get_data(22126)), 2, set_bonus=0.62, set_multiplier=1.1),
        Implant(*(await get_data(22129)), 3, set_bonus=0.75, set_multiplier=1.1),
        Implant(*(await get_data(22127)), 4, set_bonus=0.88, set_multiplier=1.1),
        Implant(*(await get_data(22128)), 5, set_bonus=1, set_multiplier=1.1),
        Implant(*(await get_data(22130)), 6, set_bonus=0, set_multiplier=2.5),

        # HG Snake
        Implant(*(await get_data(19540)), 1, set_bonus=0.5, set_multiplier=1.15),
        Implant(*(await get_data(19551)), 2, set_bonus=0.62, set_multiplier=1.15),
        Implant(*(await get_data(19553)), 3, set_bonus=0.75, set_multiplier=1.15),
        Implant(*(await get_data(19554)), 4, set_bonus=0.88, set_multiplier=1.15),
        Implant(*(await get_data(19555)), 5, set_bonus=1, set_multiplier=1.15),
        Implant(*(await get_data(19556)), 6, set_bonus=0, set_multiplier=3),

        # Navigation Implants
        Implant(*(await get_data(27097)), 6, bonus=1),
        Implant(*(await get_data(3096)), 6, bonus=2),
        Implant(*(await get_data(13237)), 6, bonus=3),
        Implant(*(await get_data(3097)), 6, bonus=4),
        Implant(*(await get_data(16003)), 6, bonus=5),
        Implant(*(await get_data(3100)), 6, bonus=6),
        Implant(*(await get_data(24669)), 6, bonus=8),

        # Zor's Custom Navigation Hyperlink
        Implant(*(await get_data(24663)), 8, bonus=5)
    ]


@alru_cache(ttl=1800)
async def talismans():
    return [
        # You declare the implants you want like this
        Implant(*(await get_data(33965)), 1, set_bonus=1.0101, set_multiplier=1.02),
        Implant(*(await get_data(33966)), 2, set_bonus=2.0202, set_multiplier=1.02),
        Implant(*(await get_data(33969)), 3, set_bonus=3.0303, set_multiplier=1.02),
        Implant(*(await get_data(33967)), 4, set_bonus=4.0404, set_multiplier=1.02),
        Implant(*(await get_data(33968)), 5, set_bonus=5.0505, set_multiplier=1.02),
        Implant(*(await get_data(33970)), 6, set_bonus=0, set_multiplier=1.1),
        # MG
        Implant(*(await get_data(22131)), 1, set_bonus=1.0101, set_multiplier=1.1, ),
        Implant(*(await get_data(22133)), 2, set_bonus=2.0202, set_multiplier=1.1, ),
        Implant(*(await get_data(22136)), 3, set_bonus=3.0303, set_multiplier=1.1, ),
        Implant(*(await get_data(22134)), 4, set_bonus=4.0404, set_multiplier=1.1, ),
        Implant(*(await get_data(22135)), 5, set_bonus=5.0505, set_multiplier=1.1, ),
        Implant(*(await get_data(22137)), 6, set_bonus=0, set_multiplier=1.25, ),
        # HG
        Implant(*(await get_data(19534)), 1, set_bonus=1.0101, set_multiplier=1.15, ),
        Implant(*(await get_data(19535)), 2, set_bonus=2.0202, set_multiplier=1.15, ),
        Implant(*(await get_data(19536)), 3, set_bonus=3.0303, set_multiplier=1.15, ),
        Implant(*(await get_data(19537)), 4, set_bonus=4.0404, set_multiplier=1.15, ),
        Implant(*(await get_data(19538)), 5, set_bonus=5.0505, set_multiplier=1.15, ),
        Implant(*(await get_data(19539)), 6, set_bonus=0, set_multiplier=1.5, ),
    ]


async def command_amulets(arguments, message):
    await send_best(arguments, message, await amulets(), "amulets")


async def command_ascendancies(arguments, message):
    await send_best(arguments, message, await ascendancies(), "ascendancies")


async def command_asklepians(arguments, message):
    await send_best(arguments, message, await asklepians(), "asklepians")


async def command_crystals(arguments, message):
    await send_best(arguments, message, await crystals(), "crystals")


async def command_snakes(arguments, message):
    await send_best(arguments, message, await snakes(), "snakes")


async def command_talismans(arguments, message):
    await send_best(arguments, message, await talismans(), "talismans")
