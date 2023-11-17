from utils import isk


class Implant:
    """Holds all the numbers for one implant."""

    def __init__(self, type_id=0, name="", price=0, slot=1, set_bonus=0.0, set_multiplier=1.0, bonus=0.0):
        self.name = name
        self.slot = slot
        self.type_id = type_id
        self.set_bonus = set_bonus
        self.set_multiplier = set_multiplier
        self.bonus = bonus
        self.price = price

    def __str__(self):
        if self.name == "":
            return ""
        else:
            return self.name + "\n"


class ImplantSet:
    """Holds all the numbers for a set of implants which affect the same attribute."""

    def __init__(self, implants):
        self.implants = implants
        self.relational_efficiency = 0

    @property
    def bonus(self):
        multiplier = 1
        for implant in self.implants:
            multiplier *= implant.set_multiplier

        bonus = 1
        for implant in self.implants:
            bonus *= (1 + implant.bonus * 0.01) * (1 + implant.set_bonus * 0.01 * multiplier)
        return bonus

    @property
    def price(self):
        return sum(implant.price for implant in self.implants)

    def __str__(self):
        if self.bonus == 1:
            return "**No stat increase for 0 isk (*infinite value!*)**\n"
        return f"**{self.bonus:.4} stat increase for {isk(self.price)} ** ({isk(self.price / (self.bonus - 1) / 100)} per %):\n" \
               f"{''.join(str(i) for i in self.implants)}"
