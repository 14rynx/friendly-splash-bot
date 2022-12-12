async def command_heat(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage:\n !heat <total_slots> <guns>")
        return

    if "show" in arguments:
        guns = [1 if x in "Xx" else 0 for x in arguments["show"][0]]

        factor = 0
        if "factor" in arguments:
            factor = arguments["factor"]
        elif "f" in arguments:
            factor = arguments["f"]

        answer = functor(guns, factor=factor)

        await message.channel.send(answer)
        return

    total, guns = arguments[""]
    total = int(total)
    guns = int(guns)

    if guns > total:
        await message.channel.send("More guns than slots doesn't work")
        return

    empty = int(total - guns)
    await message.channel.send("x" * (guns // 2) + "-" * (empty // 2) + "x" * (guns%2) + "-" * (empty - empty // 2)  + "x" * (guns // 2) )


class MessageFunctor:
    def __init__(self):
        self.last = False
        self.average = 0
        self.max = 0

    def __call__(self, guns, factor=None):
        output = calc_heat(guns)

        new_average = sum(output) / len(output)
        new_max = max(output)

        if self.last:
            change_avg = f"({abs(new_average - self.average):.3f} " + (
                "lower than last run)" if new_average < self.average else "higher than last run)")
            change_max = f"({abs(new_max - self.max):.3f} " + (
                "lower than last run)" if new_max < self.max else "higher than last run)")
        else:
            change_avg, change_max = "", ""
            self.last = True

        self.average = new_average
        self.max = new_max

        ret = [
            '**Heat for Arrangement:**',
            " ".join([f"{s}        " for s in guns]),
            " ".join([f"{s:.3f}" for s in output]),
            "",
            f"Average:      {self.average:.3f}    {change_avg}",
            f"Maximum:  {self.max:.3f}    {change_max}"
        ]

        return "\n".join(ret)


def calc_heat(guns, factor=None):
    if factor is None or factor == 0:
        factor_dict = {
            8: 0.82,
            7: 0.79,
            6: 0.76,
            5: 0.71,
            4: 0.63,
            3: 0.50,
            2: 0.25,
            1: 1
        }
        factor = factor_dict[len(guns)]

    output = [0] * len(guns)

    for x_dist, val in enumerate(guns):
        for y_dist in range(len(output)):
            output[y_dist] += val * factor ** (abs(x_dist - y_dist))

    return output


global functor
functor = MessageFunctor()
