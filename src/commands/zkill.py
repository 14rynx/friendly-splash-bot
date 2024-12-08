from math import floor

from discord.ext import commands

from network import *
from utils import command_error_handler


def find_kill_id(zkill_link: str) -> int:
    try:
        kill_id = int(zkill_link.split("/")[-2])
    except IndexError:
        raise ValueError(f"Invalid zkill_link: {zkill_link}")

    return kill_id


async def get_rig_size(ship_type_id):
    try:
        if (await get_group_id(ship_type_id)) == 963:  # Strategic Cruisers
            return 2
        return int(await get_dogma_attribute(ship_type_id, 1547))
    except TypeError:
        return 1


class ItemHelper:
    """Helper class to get all attributes needed of an item at once."""

    def __init__(self, type_id, quantity=1, ):
        self.type_id = type_id
        self.quantity = quantity

    async def fetch(self):
        self.item_data = await get_item_data(self.type_id)
        self.name = self.item_data.get("name", f"Unknown Item (type_id={self.type_id})")
        self.group_id = self.item_data.get("group_id")

        self.group_data = await get_group_data(self.group_id)
        self.category_id = self.group_data.get("category_id")

        self.dogma_attributes = {}
        for item in self.item_data.get("dogma_attributes"):
            self.dogma_attributes[int(item["attribute_id"])] = item["value"]

        self.meta_level = self.dogma_attributes.get(633)
        self.is_heatable = self.dogma_attributes.get(1211)
        self.is_dda = self.group_id == 645
        self.is_miner = self.group_id == 54
        self.is_structure = self.group_id == 65

        if self.group_id == 963:  # Strategic Cruisers
            self.rig_size = 2
        self.rig_size = self.dogma_attributes.get(1547)


@commands.command()
@command_error_handler
async def explain(ctx, zkill_link):
    """Explains how a kill came to have those points"""

    try:
        kill_id = find_kill_id(zkill_link)
    except ValueError as instance:
        await ctx.send(f"Could not parse zkill link!")
        return

    out = []

    # Fetch killmail
    kill_hash = await get_hash(kill_id)
    kill_data = await get_kill(kill_id, kill_hash)

    victim_ship_type_id = kill_data.get("victim", {}).get("ship_type_id")
    if victim_ship_type_id:
        victim_rig_size = await get_rig_size(victim_ship_type_id)
    else:
        victim_rig_size = 1

    base_points = 5 ** victim_rig_size
    out.append(f"Ship Base Points: {base_points}")

    # Items on Victim Ship Stuff
    out.append("Looking at Items:")

    # Preselect interesting items
    items = []
    for raw_item in kill_data.get("victim", {}).get("items", []):
        if not "item_type_id" in raw_item:
            continue

        if 11 <= raw_item.get("flag", -1) < 35 or 125 <= raw_item.get("flag", -1) < 129:
            items.append(
                ItemHelper(
                    type_id=raw_item.get("item_type_id"),
                    quantity=raw_item.get("quantity_dropped", 0) + raw_item.get("quantity_destroyed", 0)
                )
            )

    # Fetch all required information for items
    await asyncio.gather(*[i.fetch for i in items])

    # Parse item information
    danger = 0
    for item in items:
        if item.category_id != 7:
            continue

        danger_points = 1 + item.meta_level // 2

        if item.is_heatable or item.is_dda:
            out.append(f"   {item.quantity}x {item.name} added {danger_points} points each")
            danger += item.quantity * danger_points

        if item.is_miner:
            out.append(f"   {item.quantity}x {item.name} subtracted {danger_points} points each")
            danger -= item.quantity * danger_points

    # Apply danger rating to items
    points = base_points + danger
    if danger < 4:
        points *= max(0.01, danger / 4)  # If the ship has more than 4 heatable modules this doesn't do anything
        out.append(f"=> Ship was of low danger, reduced points by ({max(0.01, danger / 4)}) to {points}")
    else:
        out.append(f"=> Increased Points to {floor(points)} (by {danger}) due to items fitted.")

    # Reducing things by amount of Attackers
    attackers_amount = len(kill_data.get("attackers", []))
    involved_penalty = max(1.0, attackers_amount ** 2 / 2)
    out.append(f"Looking at attacker amount:")
    out.append(f"Total of {attackers_amount} attacker(s).")
    points /= involved_penalty
    out.append(
        f"=> Reducing points by {100 * (1 - 1 / involved_penalty):.1f} % to {floor(points)} for the amount of attackers")

    # Preselecting attacker information
    characters = 0
    attacker_ships = []
    maybe_structure = []
    for attacker in kill_data.get("attackers", []):
        ship_type_id = attacker.get("ship_type_id")
        if not ship_type_id:
            continue

        if "character_id" in attacker:
            characters += 1

            attacker_ships.append(
                ItemHelper(
                    type_id=ship_type_id
                )
            )
        else:
            maybe_structure.append(ship_type_id)

    # Throwing out NPC Killmails
    if characters == 0:
        out.append("NPC Killmail -> Giving 1 Point and throwing everything else out the window.")
        await ctx.send("\n".join(out))
        return

    # Fetch all required information for the attackers
    attacker_task =  asyncio.gather(*[i.fetch for i in attacker_ships])
    structure_task = asyncio.gather(*[is_structure(t) for t in maybe_structure])
    _, structure_results = await asyncio.gather(attacker_task, structure_task)

    # Parse attacker information
    out.append("Looking at attacker sizes:")
    attackers_total_size = 0
    if any(a.is_structure for a in attacker_ships) or any(structure_results) :
        out.append("Structure on Killmail => Giving 1 Point and throwing everything else out the window.")
        await ctx.send("\n".join(out))
        return

    for attacker in attacker_ships:
        if attacker.group_id == 29:  # Capsule
            attackers_total_size += 5 ** (victim_rig_size + 1)
            out.append(
                f"   Capsule added {5 ** (victim_rig_size + 1)} to enemy size")
        else:
            attackers_total_size += 5 ** attacker.rig_size
            out.append(
                f"   {attacker.name} added {5 ** attacker.rig_size} to enemy size")

    average_size = max(1.0, attackers_total_size / attackers_amount)
    out.append(f"Average attacker size is {average_size}, victim size is {base_points}")

    ship_size_modifier = min(1.2, max(0.5, floor(base_points / average_size)))
    points = floor(points * ship_size_modifier)
    if ship_size_modifier > 1:
        out.append(
            f"=> Increasing points by {100 * (ship_size_modifier - 1):.1f} % to {points} for the size of attackers")
    elif ship_size_modifier < 1:
        out.append(
            f"=> Reducing points by {100 * (1 - ship_size_modifier):.1f} % to {points} for the size of attackers")

    if points < 1:
        out.append("The kill was worthless, but I have to give one point anyway")

    out.append(f"Resulted in {floor(points)} points.")

    await ctx.send("\n".join(out))


async def setup(bot):
    bot.add_command(explain)
