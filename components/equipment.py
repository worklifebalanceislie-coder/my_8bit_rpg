class Equipment:
    def __init__(self):
        self.slots = {
            "weapon": None,
            "armor": None,
            "pants": None,
            "boots": None,
            "ring": None,
            "amulet": None,
            "backpack": None
        }

    def equip(self, item, inventory):
        if item.type not in self.slots:
            return False

        # Если меняем один рюкзак на другой, проверяем, хватит ли места после замены
        if item.type == "backpack" and self.slots["backpack"] is not None:
            old_cap = self.slots["backpack"].stats_bonus.get("capacity", 0)
            new_cap = item.stats_bonus.get("capacity", 0)
            if inventory.capacity - old_cap + new_cap < len(inventory.items):
                return False

            # Меняем рюкзаки напрямую
            old_bag = self.slots["backpack"]
            if inventory.remove_item(item):
                self.slots["backpack"] = item
                inventory.add_item(old_bag)
                return True
            return False

        if self.slots[item.type] is not None:
            if not self.unequip(item.type, inventory):
                return False

        if inventory.remove_item(item):
            self.slots[item.type] = item
            return True
        return False

    def unequip(self, slot_name, inventory):
        item = self.slots.get(slot_name)
        if not item:
            return False

        # Нельзя снять рюкзак, если без него в карманах не хватит места (учитывая сам снимаемый рюкзак)
        if slot_name == "backpack":
            bag_bonus = item.stats_bonus.get("capacity", 0)
            if len(inventory.items) + 1 > inventory.capacity - bag_bonus:
                return False

        if inventory.add_item(item):
            self.slots[slot_name] = None
            return True
        return False

    def get_total_bonus(self, stat_name):
        total = 0
        for item in self.slots.values():
            if item and stat_name in item.stats_bonus:
                total += item.stats_bonus[stat_name]
        return total
