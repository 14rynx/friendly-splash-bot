import math

from discord.ext import commands

from utils import convert, unix_style_arg_parser


class State:
    def __init__(self, nominal_mass, ships, already_through_min=0, already_through_max=0):

        if already_through_min > already_through_max:
            raise ValueError

        # Fixed Values
        self.NOMINAL_MASS = nominal_mass
        self.THROUGH_MIN = already_through_min
        self.THROUGH_MAX = already_through_max

        self.windows = {
            "Reduced": 0.5,
            "Crit": 0.1
        }

        self.ships = sorted(ships, key=lambda x: x.options[0], reverse=True)

        self.all_options = [option for x in self.ships for option in x.options]

        # These values might change over time
        self.min = self.NOMINAL_MASS * 0.9 - already_through_max
        self.max = self.NOMINAL_MASS * 1.1 - already_through_min
        self.jumped_so_far = 0

    @property
    def thresholds(self):
        for name, value in self.windows.items():
            yield [value, name, self.NOMINAL_MASS * 0.9 * value, self.NOMINAL_MASS * 1.1 * value]

    def jump(self, mass):
        self.max -= mass
        self.min -= mass
        self.jumped_so_far += mass

    def revert(self, mass):
        self.max += mass
        self.min += mass
        self.jumped_so_far -= mass


class Ship:
    def __init__(self, name, options, amount=1):
        self.name = name
        self.options = options
        self.amount = amount
        self.cycle = 0
        self.side = 0

    def jump(self):
        self.cycle += self.side
        self.side = 1 - self.side

    def revert(self):
        self.side = 1 - self.side
        self.cycle -= self.side

    @property
    def cycles_multi(self):
        return math.floor(self.cycle / self.amount)


def priority(ship, state):
    # This function is more snake oil than exact math, removing any term might make it still work, but maybe a little better or worse
    cycle_term = ship.cycle
    side_term = ship.side / 2 if state.jumped_so_far < 0.5 * state.NOMINAL_MASS else - ship.side / 2
    mass_term = - abs(state.min - ship.options[0]) / max(state.min, ship.options[0])
    return cycle_term + side_term + mass_term


def skip(option, ship, state, depth):
    # This function is more snake oil than exact math, removing any term might make it still work, but maybe a little better or worse
    return option < sorted(state.all_options, reverse=True)[depth]


def player(state, depth=1):
    for ship in sorted(state.ships, key=lambda x: priority(x, state)):
        for option in ship.options:

            if skip(option, ship, state, depth):
                continue

            ship.jump()
            state.jump(option)
            works, paths = enviroment(state, depth)
            ship.revert()
            state.revert(option)

            if works:
                return True, [[ship.name, option, ship.cycles_multi, "<- " if ship.side == 1 else " ->"]] + paths

    return False, []


def enviroment(state, depth=1):
    # It could roll
    if state.min < 0:
        # It rolled for certain and there are no ships outside
        if state.max <= 0 and sum(x.side for x in state.ships) == 0:
            return True, []
        return False, []

    for nominal, name, mi, ma in state.thresholds:
        if state.max > mi and state.min < ma and state.jumped_so_far > (state.NOMINAL_MASS * 0.9 - mi):

            # Calculate new mass ranges
            th_max = min(state.max, ma, nominal / (1 - nominal) * (state.jumped_so_far + state.THROUGH_MAX))
            th_min = max(state.min, mi, nominal / (1 - nominal) * (state.jumped_so_far + state.THROUGH_MIN))

            # Over Treshold
            old_max = state.max  # Save
            state.max = th_max
            works_over, path_over = player(state, depth)
            state.max = old_max  # Revert

            # There are no other cases
            if th_max >= state.max:
                return works_over, path_over

            # Under Treshold
            old_min = state.min  # Save
            state.min = th_min
            works_under, path_under = player(state, depth)
            state.min = old_min  # Revert

            # Deduplicate Result
            if path_over == path_under:
                return works_over & works_under, path_over

            # Return Full Result
            return works_over & works_under, [{(True, name, th_max, state.min): path_over,
                                               (False, name, state.max, th_min): path_under}]

    # No special action has to be taken
    return player(state, depth)


def print_path(li, indent=0):
    ret = ""
    for x in li:
        if type(x) == list:
            ship, mass, pass_nr, direction = x
            ret += "." * indent + f"{ship} {mass} {pass_nr} {direction}\n"
        else:
            for (boolean, name, max, min), value in x.items():
                ret += "." * indent + f"**If it is{'' if boolean else ' not'} {name.lower()}** ({min:.2f} {max:.2f})\n"
                ret += print_path(value, indent + 1)
    return ret


def metasolver(state):
    for depth in range(1, len(state.all_options)):
        works, path = player(state, depth)
        if works:
            return works, path

    return False, []


@commands.command()
async def roll(ctx, *args):
    """
    !roll <wh_nominal_mass>
        --<Ship_name>|-<ship_letter> <mass1> [<mass2>, ...]
        [--<ship_name_2>| ...]*
    """

    arguments = unix_style_arg_parser(args)

    try:
        # Todo: Additional Arguments
        wh = State(
            convert(arguments[""][0]),  # already_through_min=2800, already_through_max=2800),
            [Ship(name, [convert(v) for v in values]) for name, values in arguments.items() if name != ""]
        )

        works, path = metasolver(wh)

        if works:
            await ctx.send("**It works, as following**\n" + print_path(path))
        else:
            await ctx.send("**Rolling like this is not possible.**")
    except Exception as e:
        await ctx.send("Could not use this data to calculate a valid rolling solution. " + help_message)


async def setup(bot):
    bot.add_command(roll)
