import logging
import random

from discord.ext import commands

# Configure the logger
logger = logging.getLogger('discord.heat')
logger.setLevel(logging.INFO)


@commands.command()
async def teams(ctx, *pilots):
    """
    !teams <name_1>, [<name_2>,] ...
    """
    logger.info(f"{ctx.author.name} used !stonks {pilots}")
    try:
        pilots = list(pilots)
        team_size = len(pilots) // 2
        random.shuffle(pilots)
        await ctx.send(
            "\n".join(
                [f"Referee: {pilots[-1]}" if len(pilots) % 2 else ""]
                + ["1:"] + pilots[:team_size]
                + ["2:"] + pilots[team_size: 2 * team_size]
            )
        )
    except Exception as e:
        await ctx.send(f"Could not use Arguments.")


async def setup(bot):
    bot.add_command(teams)
