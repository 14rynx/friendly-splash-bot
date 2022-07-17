import random


async def command_teams(arguments, message):

    if "help" in arguments:
        await message.channel.send("Usage:\n!teams <name_1>, [<name_2>,] ...")
        return

    pilots = arguments[""]
    team_size = len(pilots) // 2
    random.shuffle(pilots)
    await message.channel.send(
        "\n".join(
            [f"Referee: {pilots[-1]}" if len(pilots) % 2 else ""]
            + ["1:"] + pilots[:team_size]
            + ["2:"] + pilots[team_size: 2 * team_size]
        )
    )
