import asyncio

import aiohttp

from commands.implants.classes import Implant
from utils import get_item_attributes
from utils import get_item_name, get_item_price


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
