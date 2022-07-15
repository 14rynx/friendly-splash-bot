import requests


def lookup(string, return_type):
    """Tries to find an ID related to the input
    Parameters
    ----------
    string : str
        The sound the animal makes (default is None)
    return_type : str
        what kind of id should be tried to match
        can be character, corporation and alliance

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
    return format(number, ",.0f").replace(',',"'") + " ISK"


def convert(number_string):
    exponent = 3 * number_string.lower().count("k") + 6 * number_string.lower().count("m") + 9 * number_string.lower().count("b")
    number = float(number_string.lower().replace("k", "").replace("m", "").replace("b", ""))
    return number * 10 ** exponent

