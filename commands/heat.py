async def command_heat(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !heat <total_slots> <guns>")
        return

    total, guns = arguments[""]
    total = int(total)
    guns = int(guns)

    if guns > total:
        await message.channel.send("More guns than slots doesn't work")
        return

    empty = int(total - guns)
    await message.channel.send("x" * (guns // 2) + "-" * (empty // 2) + "x" * (guns%2) + "-" * (empty - empty // 2)  + "x" * (guns // 2) )
