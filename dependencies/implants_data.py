import aiohttp
from dependencies.utils import isk, convert
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
                print(f"{self} costs: {isk(self.price)}")

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
        print(self.min_price, item.price, self.max_price)
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
