from dependencies.utils import lookup
from dependencies.corp_statistics import get_corp_statistics


async def corp(arguments, message):

    name = " ".join(arguments[""])
    id = lookup(name, 'corporations')

    response = await get_corp_statistics(id)
    await message.channel.send(response)
