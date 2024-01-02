class Module:
    def __init__(self, json):
        self.type_id = json['type_id']
        self.item_id = json["id"]
        self.mutator_type_id = json['mutator_type_id']
        self.source_type_id = json['source_type_id']
        self.contract_id = json['latest_contract_id']

        # Make dictionary with attributes
        self.mutated_attributes = {}
        for attribute in json.get("attributes"):
            self.mutated_attributes[attribute["attribute_id"]] = float(attribute["value"])

        self.basic_attributes = {}

        # Calculate shield booster stats
        try:
            self.mutated_attributes[420001] = self.mutated_attributes[68] / self.mutated_attributes[73] * 1000
            self.mutated_attributes[420002] = self.mutated_attributes[68] / self.mutated_attributes[6]
            self.mutated_attributes[420003] = self.mutated_attributes[6] / self.mutated_attributes[73] * 1000
        except KeyError:
            pass

        # Add price stat
        self.mutated_attributes[0] = json.get("contract").get("unified_price")

    @property
    def attributes(self):
        attrs = self.basic_attributes
        attrs.update(self.mutated_attributes)
        return attrs

    async def fetch(self, session):
        async with session.get(f"https://esi.evetech.net/latest/universe/types/{self.source_type_id}/") as response:
            data = await response.json()
            for attribute in data.get("dogma_attributes"):
                if attribute["attribute_id"] not in self.basic_attributes:
                    self.basic_attributes[attribute["attribute_id"]] = float(attribute["value"])

    def url(self, number=1):
        return f"[Abyssal Module {number}](https://mutamarket.com/modules/{self.item_id})"
