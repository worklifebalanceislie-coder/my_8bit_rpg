from items import ITEMS_DB

PROFESSIONS_DB = {}  # Заполняется из таблицы professions_catalog в rpg.db
RECIPES_DB = {}      # Заполняется из таблицы recipes_catalog в rpg.db


class ProfessionInfo:
    def __init__(self, prof_id, name, desc, bonus_type="craft"):
        self.id = prof_id
        self.name = name
        self.desc = desc
        self.bonus_type = bonus_type  # 'craft', 'trade', 'gather'


class Recipe:
    def __init__(self, recipe_id, prof_id, result_item_id, req_level, materials, xp_gain=20):
        self.id = recipe_id
        self.prof_id = prof_id
        self.result_item_id = result_item_id
        self.req_level = req_level
        self.materials = materials  # Словарь {item_id: count}
        self.xp_gain = xp_gain


class ProfessionBook:
    def __init__(self, owner):
        self.owner = owner
        # Словарь изученных профессий: {prof_id: {"level": 1, "xp": 0, "xp_next": 100}}
        self.learned = {}

    def learn(self, prof_id, level=1):
        if prof_id not in PROFESSIONS_DB:
            return False, "Неизвестная профессия"
        if prof_id in self.learned:
            return False, f"Профессия '{PROFESSIONS_DB[prof_id].name}' уже изучена!"
        self.learned[prof_id] = {"level": level, "xp": 0, "xp_next": level * 100}
        return True, f"Изучена профессия: {PROFESSIONS_DB[prof_id].name}!"

    def has_profession(self, prof_id):
        return prof_id in self.learned

    def get_level(self, prof_id):
        return self.learned[prof_id]["level"] if prof_id in self.learned else 0

    def add_xp(self, prof_id, amount):
        if prof_id not in self.learned:
            return False
        data = self.learned[prof_id]
        data["xp"] += amount
        leveled = False
        while data["xp"] >= data["xp_next"]:
            data["xp"] -= data["xp_next"]
            data["level"] += 1
            data["xp_next"] = data["level"] * 100
            leveled = True
        return leveled

    def can_craft(self, recipe):
        if not self.owner.inventory:
            return False, "Нет инвентаря"
        if self.get_level(recipe.prof_id) < recipe.req_level:
            return False, f"Нужен уровень профессии: {recipe.req_level}"
        if recipe.result_item_id not in ITEMS_DB:
            return False, "Неизвестный предмет"

        for mat_id, req_qty in recipe.materials.items():
            have = sum(1 for it in self.owner.inventory.items if it.id == mat_id)
            if have < req_qty:
                mat_name = ITEMS_DB[mat_id].name if mat_id in ITEMS_DB else mat_id
                return False, f"Не хватает: {mat_name} ({have}/{req_qty})"

        return True, "Можно создать"

    def craft(self, recipe):
        ok, msg = self.can_craft(recipe)
        if not ok:
            return False, msg

        # Списываем ресурсы из инвентаря
        for mat_id, req_qty in recipe.materials.items():
            removed = 0
            for it in list(self.owner.inventory.items):
                if it.id == mat_id and removed < req_qty:
                    self.owner.inventory.remove_item(it)
                    removed += 1

        res_item = ITEMS_DB[recipe.result_item_id]
        if not self.owner.inventory.add_item(res_item):
            # Если рюкзак переполнен, возвращаем ресурсы обратно
            for mat_id, req_qty in recipe.materials.items():
                for _ in range(req_qty):
                    self.owner.inventory.add_item(ITEMS_DB[mat_id])
            return False, "Рюкзак переполнен!"

        leveled = self.add_xp(recipe.prof_id, recipe.xp_gain)
        lvl_txt = f" (Уровень профессии повышен до {self.get_level(recipe.prof_id)}!)" if leveled else ""
        return True, f"Создано: {res_item.name}!{lvl_txt}"
