class Inventory:
    def __init__(self, capacity=4, gold=0):
        self.base_capacity = capacity
        self.gold = gold
        self.items = []
        self.equipment = None  # Ссылка на модуль экипировки

    @property
    def capacity(self):
        """Динамически считает вместимость: базовые карманы + бонус от рюкзака"""
        bonus = self.equipment.get_total_bonus("capacity") if self.equipment else 0
        return self.base_capacity + bonus

    def add_item(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)
            return True
        return False

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def transfer_to(self, target_inventory, item):
        if item in self.items and target_inventory.add_item(item):
            self.remove_item(item)
            return True
        return False
