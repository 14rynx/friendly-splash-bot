import aiohttp

from commands.damage_mods.classes import DamageMod
from utils import get_urls


async def get_abyssals_esi(type_id: int):
    async with aiohttp.ClientSession() as session:
        p_urls = [f"https://esi.evetech.net/latest/contracts/public/10000002/?page={page}" for page in range(1, 100)]
        async for page in get_urls(p_urls, session):

            # Sort out pages that don't exist
            if type(page) == dict and "error" in page:
                continue

            interesting_contracts = [contract for contract in page if contract["type"] == "item_exchange"]
            c_ids = [contract["contract_id"] for contract in interesting_contracts]
            c_urls = [f"https://esi.evetech.net/latest/contracts/public/items/{c_id}/" for c_id in c_ids]
            c_prices = [contract["price"] for contract in interesting_contracts]
            async for c_items, (c_id, c_price) in get_urls(c_urls, session, zip(c_ids, c_prices)):

                # Sort out empty contracts
                if not c_items:
                    continue

                # Sort out contracts for 0 ISK
                if c_price == 0:
                    continue

                # Sort out any contracts asking for some item (item not is_included = True in the contract)
                if not all([bool(item["is_included"]) for item in c_items if "is_included" in item]):
                    continue

                i_ids = [(item['type_id'], item['item_id']) for item in c_items if
                         "type_id" in item and int(item["type_id"]) == type_id]
                i_urls = [f"https://esi.evetech.net/latest/dogma/dynamic/items/{i_type_id}/{i_item_id}/" for
                          i_type_id, i_item_id in i_ids]
                async for item_attributes, (i_type_id, i_item_id) in get_urls(i_urls, session, i_ids):
                    if "dogma_attributes" not in item_attributes:
                        continue

                    attributes = {a.get("attribute_id"): a.get("value") for a in item_attributes.get("dogma_attributes", {})}

                    yield DamageMod(
                        price=c_price,
                        type_id=i_type_id,
                        module_id=i_item_id,
                        contract_id=c_id,
                        attributes=attributes,
                    )


async def get_abyssals_mutamarket(type_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"https://mutamarket.com/api/modules/type/{type_id}/item-exchange/contracts-only/") as response:
            for item in await response.json():
                if not (contract := item.get("contract")):
                    continue

                if not contract.get("type") == "item_exchange":
                    continue

                if not contract.get("region_id", 10000002) == 10000002:
                    continue

                if not contract.get("plex_count", 0) == 0:
                    continue

                if contract.get("asking_for_items", True):
                    continue

                attributes = {a.get("id"): a.get("value") for a in item.get("mutated_attributes", [])}

                yield DamageMod(
                    price=contract.get("price"),
                    type_id=item.get("mutator_type_id"),
                    module_id=item.get("id"),
                    contract_id=contract.get("id"),
                    attributes=attributes,
                )


async def get_cheapest(item_ids):
    cheapest_price = float("inf")
    cheapest_id = 0

    async with aiohttp.ClientSession() as session:
        urls = [f"https://market.fuzzwork.co.uk/aggregates/?region=10000002&types={i}" for i in item_ids]
        async for item_prices, item_id in get_urls(urls, session, item_ids):
            item_price = float(item_prices[str(item_id)]["sell"]["min"])
            if item_price < 100:
                continue
            if item_price < cheapest_price:
                cheapest_price = item_price
                cheapest_id = item_id

    return cheapest_price, cheapest_id
