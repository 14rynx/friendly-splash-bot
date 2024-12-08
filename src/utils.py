import functools

import logging

# Configure the logger
logger = logging.getLogger('discord.utils')
logger.setLevel(logging.INFO)


def isk(number):
    """Takes a number and converts it into an ingame-like ISK format string.

    Parameters
    ----------
    number : int / float
        amount of Interstellar Kredits to display
    """

    return format(number, ",.0f").replace(',', "'") + " ISK"


def convert(number_string):
    """Takes a number-string and converts it into a number, taking common abbreviations.

    Parameters
    ----------
    number_string : str
        something like 1b, 15m 10kk
    """
    exponent = 3 * number_string.lower().count("k") + 6 * number_string.lower().count(
        "m") + 9 * number_string.lower().count("b")
    number = float(number_string.lower().replace("k", "").replace("m", "").replace("b", ""))
    return number * 10 ** exponent


class RelationalSorter:
    @staticmethod
    def interpolate(x1, y1, x2, y2, x_target):
        assert (x1 <= x_target <= x2)
        dx = x2 - x1
        rx = x_target - x1
        dy = y2 - y1

        if dx != 0:
            return y1 + dy / dx * rx
        else:
            return y1

    def __init__(self, all_points):
        # Add edge points to make sure it works properly
        all_points.append((0, 0))
        all_points.append((float("inf"), max([y for x, y in all_points])))

        self.best = list(sorted(all_points, key=lambda x: x[0]))

        old_len = 0
        while (old_len != len(self.best)):
            old_len = len(self.best)

            interpolated_prices = [0] + [
                RelationalSorter.interpolate(*self.best[i - 1], *self.best[i + 1], self.best[i][0]) for i in
                range(1, len(self.best) - 1)] + [0]
            self.best = [i for i, j in zip(self.best, interpolated_prices) if i[1] > j]

    def __call__(self, point):
        try:
            index = next(i for i, val in enumerate(self.best) if val[0] > point[0])
        except StopIteration:
            return 1.0
        else:
            interpolated_bonus = RelationalSorter.interpolate(*self.best[index - 1], *self.best[index], point[0])
            return point[1] / interpolated_bonus


def unix_style_arg_parser(args, separator=" ", letter_argument="-", word_argument="--"):
    message = " ".join(args)
    elements = message.split(separator)
    arguments = {}
    key = ""
    values = []

    for element in elements:
        element.strip()

        if element[0:2] == word_argument:
            if values:
                arguments.update({key: values})
            key = element.strip(word_argument)
            values = []

        elif element[0] == letter_argument:
            if values:
                arguments.update({key: values})
            for x in element.strip(letter_argument)[:-1]:
                arguments.update({x: []})
            key = element.strip(letter_argument)[-1]
            values = []

        else:
            values.append(element)

    arguments.update({key: values})

    return arguments


def command_error_handler(func):
    """Decorator for handling bot command logging and exceptions."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ctx = args[0]
        logger.info(f"{ctx.author.name} used !{func.__name__}")

        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in !{func.__name__} command: {e}", exc_info=True)
            await ctx.send(f"An error occurred in !{func.__name__}.")

    return wrapper
