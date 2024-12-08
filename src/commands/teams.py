import random

from discord.ext import commands

from utils import command_error_handler


@commands.command()
@command_error_handler
async def teams(ctx, *pilots):
    """
    !teams <name_1>, [<name_2>,] ...
    """
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


async def setup(bot):
    bot.add_command(teams)
