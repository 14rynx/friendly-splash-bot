import requests


def lookup(string, return_type):
    """Tries to find an ID related to the input.

    Parameters
    ----------
    string : str
        The character / corporation / alliance name
    return_type : str
        what kind of id should be tried to match
        can be characters, corporations and alliances

    Raises
    ------
    ValueError, JSONDecodeError ...
    """
    try:
        return int(string)
    except ValueError:
        try:
            response = requests.post('https://esi.evetech.net/latest/universe/ids/?datasource=tranquility&language=en',
                                     json=[string])
            return response.json()[return_type][0]["id"]
        except requests.exceptions.RequestException:
            raise ValueError


def isk(number):
    """Takes a number and converts it into an ingame-like ISK format string.

    Parameters
    ----------
    number : int / float
        amount of Interstellar Kredits to display
    """

    return format(number, ",.0f").replace(',',"'") + " ISK"


def convert(number_string):
    """Takes a number-string and converts it into a number, taking common abbreviations.

    Parameters
    ----------
    number_string : str
        something like 1b, 15m 10kk
    """
    exponent = 3 * number_string.lower().count("k") + 6 * number_string.lower().count("m") + 9 * number_string.lower().count("b")
    number = float(number_string.lower().replace("k", "").replace("m", "").replace("b", ""))
    return number * 10 ** exponent

