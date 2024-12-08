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
    danger = 0
    for item in kill_data.get("victim", {}).get("items", []):
        type_id = item.get("item_type_id")
        quantity = item.get("quantity_dropped", 0) + item.get("quantity_destroyed", 0)

        if not type_id:
            continue

        if await get_category_id(type_id) != 7:
            continue

        if "flag" in item and 11 <= item.get("flag", -1) < 35 or 125 <= item.get("flag", -1) < 129:
            meta = 1 + await get_meta_level(type_id) // 2

            if await is_heatable(type_id) or await is_dda(type_id):
                out.append(f"   {quantity}x {await get_item_name(type_id)} added {meta}")
                danger += quantity * meta

            if await is_miner(type_id):
                out.append(f"   {quantity}x {await get_item_name(type_id)} subtracted {meta}")
                danger -= quantity * meta

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

    # Looking at the Size of each Attacker
    out.append("Looking at attacker sizes:")
    characters = 0
    attackers_total_size = 0
    for attacker in kill_data.get("attackers", []):
        ship_type_id = attacker.get("ship_type_id")
        if not ship_type_id:
            continue

        if await is_structure(ship_type_id):
            out.append("Structure on Killmail => Giving 1 Point and throwing everything else out the window.")
            return 1

        if "character_id" in attacker:
            characters += 1
            group_id = await get_group_id(ship_type_id)
            rig_size = await get_rig_size(ship_type_id)
            if group_id == 29:  # Capsule
                attackers_total_size += 5 ** (victim_rig_size + 1)
                out.append(
                    f"   Capsule added {5 ** (victim_rig_size + 1)} to enemy size")
            else:
                attackers_total_size += 5 ** rig_size
                out.append(
                    f"   {await get_item_name(attacker['ship_type_id'])} added {5 ** rig_size} to enemy size")

    if characters == 0:
        out.append("NPC Killmail -> Giving 1 Point and throwing everything else out the window.")
        return 1

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
        return 1

    out.append(f"Resulted in {floor(points)} points.")

    await ctx.send("\n".join(out))


async def setup(bot):
    bot.add_command(explain)
