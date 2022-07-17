import asyncio
import aiohttp
from utils import isk, convert
import math
import ssl
import certifi
import itertools


class Implant:
    def __init__(self, id, slot, set_bonus=0.0, set_multiplier=1.0, bonus=0.0):
        self.name = "Empty"
        self.slot = slot
        self.id = id
        self.set_bonus = set_bonus
        self.set_multiplier = set_multiplier
        self.bonus = bonus
        self.price = 0

    async def fetch(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            if self.id == 0:
                self.price = 0
            else:
                async with session.get(f"https://market.fuzzwork.co.uk/aggregates/?region=10000002&types={self.id}") as response:
                    self.price = float((await response.json())[str(self.id)]["sell"]["min"])
                async with session.get(f"https://esi.evetech.net/latest/universe/types/{self.id}/") as response:
                    self.name = (await response.json())["name"]

    def __str__(self):
        return f"{self.name}"


class ImplantSet:
    def __init__(self, implants):
        self.implants = implants

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
        return f"**{self.bonus:.4} efficiency for {isk(self.price)} ** {newline}{newline.join(str(i) for i in self.implants)}"


def combinations(implants):
    slot_dict = {}
    for implant in implants:
        if implant.slot in slot_dict:
            slot_dict[implant.slot].append(implant)
        else:
            slot_dict.update({implant.slot: [implant]})
            slot_dict[implant.slot].append(Implant(0, implant.slot))

    total = 1
    for key, value in slot_dict.items():
        total *= len(value)

    for x in itertools.product(*slot_dict.values()):
        yield ImplantSet(x)


class Sorter:
    def __init__(self, min_price, max_price, order=2):
        self.min_price = min_price
        self.max_price = max_price
        self.order = order

    def __call__(self, item):
        if item.price == 0:
            return 0
        if self.min_price < item.price < self.max_price:
            if self.order >= 0:
                return (item.bonus - 1) ** self.order / item.price
            else:
                return math.exp((item.bonus - 1)) / item.price
        else:
            return 0


def get_sorter(arguments):
    if "grading" in arguments:
        if arguments["grading"][0] == "fixed":
            scale = 0
        elif arguments["grading"][0] == "linear":
            scale = 1
        elif arguments["grading"][0] == "quadratic":
            scale = 2
        elif arguments["grading"][0] == "cubic":
            scale = 3
        else:
            scale = -1
    else:
        scale = -1

    return Sorter(convert(arguments[""][0]), convert(arguments[""][1]), scale)

async def command_talismans(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !talismans <min_price> <max_price> [--grading fixed|linear|quadratic|cubic|exponential]")
        return

    implants = [
        # You declare the implants you want like this
        Implant(33965, 1, set_bonus=1.0101, set_multiplier=1.02),
        Implant(33966, 2, set_bonus=2.0202, set_multiplier=1.02),
        Implant(33967, 3, set_bonus=3.0303, set_multiplier=1.02),
        Implant(33968, 4, set_bonus=4.0404, set_multiplier=1.02),
        Implant(33969, 5, set_bonus=5.0505, set_multiplier=1.02),
        Implant(33970, 6, set_bonus=0, set_multiplier=1.1),
        # MG
        Implant(22131, 1, set_bonus=1.0101, set_multiplier=1.1),
        Implant(22133, 2, set_bonus=2.0202, set_multiplier=1.1),
        Implant(22134, 3, set_bonus=3.0303, set_multiplier=1.1),
        Implant(22135, 4, set_bonus=4.0404, set_multiplier=1.1),
        Implant(22136, 5, set_bonus=5.0505, set_multiplier=1.1),
        Implant(22137, 6, set_bonus=0, set_multiplier=1.25),
        # HG
        Implant(19534, 1, set_bonus=1.0101, set_multiplier=1.15),
        Implant(19535, 2, set_bonus=2.0202, set_multiplier=1.15),
        Implant(19536, 3, set_bonus=3.0303, set_multiplier=1.15),
        Implant(19537, 4, set_bonus=4.0404, set_multiplier=1.15),
        Implant(19538, 5, set_bonus=5.0505, set_multiplier=1.15),
        Implant(19539, 6, set_bonus=0, set_multiplier=1.5),
    ]

    await asyncio.gather(*[i.fetch() for i in implants])
    ret = "\n".join(map(str, sorted(combinations(implants), key=get_sorter(arguments), reverse=True)[:3]))
    await message.channel.send(ret)


async def command_asklepians(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !asklepians <min_price> <max_price> [--grading fixed|linear|quadratic|cubic|exponential]")
        return

    implants = [
        # LG Asklepian
        Implant(42145, 1, set_bonus=1, set_multiplier=1.02),
        Implant(42146, 2, set_bonus=2, set_multiplier=1.02),
        Implant(42202, 3, set_bonus=3, set_multiplier=1.02),
        Implant(42200, 4, set_bonus=4, set_multiplier=1.02),
        Implant(42201, 5, set_bonus=5, set_multiplier=1.02),
        Implant(42203, 6, set_bonus=0, set_multiplier=1.1),

        # MG Asklepian
        Implant(42204, 1, set_bonus=1, set_multiplier=1.1),
        Implant(42205, 2, set_bonus=2, set_multiplier=1.1),
        Implant(42206, 3, set_bonus=3, set_multiplier=1.1),
        Implant(42207, 4, set_bonus=4, set_multiplier=1.1),
        Implant(42208, 5, set_bonus=5, set_multiplier=1.1),
        Implant(42209, 6, set_bonus=0, set_multiplier=1.25),

        # HG Asklepian
        Implant(42210, 1, set_bonus=1, set_multiplier=1.15),
        Implant(42211, 2, set_bonus=2, set_multiplier=1.15),
        Implant(42212, 3, set_bonus=3, set_multiplier=1.15),
        Implant(42213, 4, set_bonus=4, set_multiplier=1.15),
        Implant(42214, 5, set_bonus=5, set_multiplier=1.15),
        Implant(42215, 6, set_bonus=0, set_multiplier=1.5),

        # Noble Repair Systems
        Implant(27070, 6, bonus=1.0101),
        Implant(3291, 6, bonus=2.0202),
        Implant(13258, 6, bonus=3.0303),
        Implant(3292, 6, bonus=4.0404),
        Implant(19547, 6, bonus=5.0505),
        Implant(3299, 6, bonus=6.0606),
        Implant(20358, 6, bonus=7.0707),

        # Noble Repair Systems
        Implant(27073, 9, bonus=1),
        Implant(3476, 9, bonus=2),
        Implant(19684, 9, bonus=3),
        Implant(3477, 9, bonus=4),
        Implant(19685, 9, bonus=5),
        Implant(3478, 9, bonus=6),

        Implant(32254, 10, bonus=3)
    ]

    await asyncio.gather(*[i.fetch() for i in implants])
    ret = "\n".join(map(str, sorted(combinations(implants), key=get_sorter(arguments), reverse=True)[:3]))
    await message.channel.send(ret)


async def command_snakes(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !snakes <min_price> <max_price> [--grading fixed|linear|quadratic|cubic|exponential]")
        return

    implants = [
        # LG Snake
        Implant(33959, 1, set_bonus=0.5, set_multiplier=1.05),
        Implant(33960, 2, set_bonus=0.62, set_multiplier=1.05),
        Implant(33963, 3, set_bonus=0.75, set_multiplier=1.05),
        Implant(33961, 4, set_bonus=0.88, set_multiplier=1.05),
        Implant(33962, 5, set_bonus=1, set_multiplier=1.05),
        Implant(33964, 6, set_bonus=0, set_multiplier=2.1),

        # MG Snake
        Implant(22125, 1, set_bonus=0.5, set_multiplier=1.1),
        Implant(22126, 2, set_bonus=0.62, set_multiplier=1.1),
        Implant(22129, 3, set_bonus=0.75, set_multiplier=1.1),
        Implant(22127, 4, set_bonus=0.88, set_multiplier=1.1),
        Implant(22128, 5, set_bonus=1, set_multiplier=1.1),
        Implant(22130, 6, set_bonus=0, set_multiplier=2.5),

        # HG Snake
        Implant(19540, 1, set_bonus=0.5, set_multiplier=1.15),
        Implant(19551, 2, set_bonus=0.62, set_multiplier=1.15),
        Implant(19553, 3, set_bonus=0.75, set_multiplier=1.15),
        Implant(19554, 4, set_bonus=0.88, set_multiplier=1.15),
        Implant(19555, 5, set_bonus=1, set_multiplier=1.15),
        Implant(19556, 6, set_bonus=0, set_multiplier=3),

        # Navigation Implants
        Implant(27097, 6, bonus=1),
        Implant(3096, 6, bonus=2),
        Implant(13237, 6, bonus=3),
        Implant(3097, 6, bonus=4),
        Implant(16003, 6, bonus=5),
        Implant(3100, 6, bonus=6),
        Implant(24669, 6, bonus=8),

        # Zor's Custom Navigation Hyperlink
        Implant(24663, 8, bonus=5)
    ]

    await asyncio.gather(*[i.fetch() for i in implants])
    ret = "\n".join(map(str, sorted(combinations(implants), key=get_sorter(arguments), reverse=True)[:3]))
    await message.channel.send(ret)


async def command_amulets(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !amulets <min_price> <max_price> [--grading fixed|linear|quadratic|cubic|exponential]")
        return

    implants = [
        # LG Amulet
        Implant(33953, 1, set_bonus=1, set_multiplier=1.02),
        Implant(33954, 2, set_bonus=2, set_multiplier=1.02),
        Implant(33957, 3, set_bonus=3, set_multiplier=1.02),
        Implant(33955, 4, set_bonus=4, set_multiplier=1.02),
        Implant(33956, 5, set_bonus=5, set_multiplier=1.02),
        Implant(33958, 6, set_bonus=0, set_multiplier=1.1),

        # MG Asklepian
        Implant(22119, 1, set_bonus=1, set_multiplier=1.1),
        Implant(22120, 2, set_bonus=2, set_multiplier=1.1),
        Implant(22123, 3, set_bonus=3, set_multiplier=1.1),
        Implant(22121, 4, set_bonus=4, set_multiplier=1.1),
        Implant(22122, 5, set_bonus=5, set_multiplier=1.1),
        Implant(22124, 6, set_bonus=0, set_multiplier=1.25),

        # HG Asklepian
        Implant(20499, 1, set_bonus=1, set_multiplier=1.15),
        Implant(20501, 2, set_bonus=2, set_multiplier=1.15),
        Implant(20507, 3, set_bonus=3, set_multiplier=1.15),
        Implant(20503, 4, set_bonus=4, set_multiplier=1.15),
        Implant(20505, 5, set_bonus=5, set_multiplier=1.15),
        Implant(20509, 6, set_bonus=0, set_multiplier=1.5),

        # Noble Hull Upgrades
        Implant(27074, 10, bonus=1.0101),
        Implant(3479, 10, bonus=2),
        Implant(13256, 10, bonus=3),
        Implant(3481, 10, bonus=4),
        Implant(19550, 10, bonus=5),
        Implant(3482, 10, bonus=6),
        Implant(21606, 10, bonus=8),

        # Imp Navy Noble
        Implant(32254, 10, bonus=3),
    ]

    await asyncio.gather(*[i.fetch() for i in implants])
    ret = "\n".join(map(str, sorted(combinations(implants), key=get_sorter(arguments), reverse=True)[:3]))
    await message.channel.send(ret)
