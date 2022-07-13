import random


async def teams(arguments, message):
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
