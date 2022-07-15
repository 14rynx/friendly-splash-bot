from dependencies import rolling_calculator
from dependencies.utils import convert


async def roll(arguments, message):
    # Todo: Additional Arguments
    wh = rolling_calculator.State(
        convert(arguments[""][0]),  # already_through_min=2800, already_through_max=2800),
        [rolling_calculator.Ship(name, [convert(v) for v in values]) for name, values in arguments.items() if name != ""]
    )

    works, path = rolling_calculator.metasolver(wh)

    if works:
        await message.channel.send("**It works, as following**\n" + rolling_calculator.print_path(path))
    else:
        await message.channel.send("**Rolling like this is not possible.**")
