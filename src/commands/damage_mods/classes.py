import asyncio
import math
import ssl

import aiohttp
import certifi

from utils import get_item_name
from utils import isk


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
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            if self.module_id is None:
                return await get_item_name(self.type_id, session)
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
