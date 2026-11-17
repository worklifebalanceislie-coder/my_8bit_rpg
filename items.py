class Item:
    def __init__(self, item_id, name, item_type, value, stats_bonus=None, description="", combat_style="melee", skill_id=None):
        self.id = item_id
        self.name = name
        self.type = item_type
        self.value = value
        self.stats_bonus = stats_bonus or {}
        self.description = description
        self.combat_style = combat_style
        self.skill_id = skill_id

    def get_stats_text(self):
        if self.type == "book":
            return "Книга навыка (Нажмите Enter в рюкзаке, чтобы изучить)"
        labels = {
            "atk": "Атака",
            "def": "Защита",
            "hp": "Макс. HP",
            "mp": "Макс. MP",
            "heal": "Лечение HP",
            "mana": "Восст. MP",
            "capacity": "Вместимость сумки"
        }
        parts = []
        for k, v in self.stats_bonus.items():
            name = labels.get(k, k)
            parts.append(f"{name}: +{v}")
        if self.type == "weapon":
            styles = {"melee": "Ближний (Сила)", "bow": "Лук (Ловкость)", "staff": "Магия (Интеллект, 10 MP)"}
            parts.append(styles.get(self.combat_style, ""))
        return ", ".join(parts) if parts else "Нет боевых бонусов"

ITEMS_DB = {
    "potion": Item("potion", "Зелье лечения", "consumable", 15, {"heal": 25}, "Восстанавливает 25 здоровья."),
    "mana_potion": Item("mana_potion", "Зелье маны", "consumable", 15, {"mana": 35}, "Восстанавливает 35 маны."),
    "rusty_sword": Item("rusty_sword", "Ржавый меч", "weapon", 30, {"atk": 3}, "Старый клинок со следами ржавчины.", "melee"),
    "iron_sword": Item("iron_sword", "Железный меч", "weapon", 75, {"atk": 7}, "Надежный клинок городской стражи.", "melee"),
    "hunting_bow": Item("hunting_bow", "Охотничий лук", "weapon", 65, {"atk": 5}, "Стреляет быстрыми стрелами на дистанции.", "bow"),
    "fire_staff": Item("fire_staff", "Посох огня", "weapon", 95, {"atk": 8}, "Выпускает огненные шары (расход: 10 MP).", "staff"),
    "leather_armor": Item("leather_armor", "Кожаная броня", "armor", 25, {"def": 2}, "Легкая куртка из дубленой кожи."),
    "chainmail": Item("chainmail", "Кольчуга", "armor", 70, {"def": 5}, "Прочная рубаха из стальных колец."),
    "leather_pants": Item("leather_pants", "Кожаные штаны", "pants", 20, {"def": 1}, "Удобные походные штаны."),
    "iron_greaves": Item("iron_greaves", "Латные поножи", "pants", 55, {"def": 3}, "Тяжелая защита для ног."),
    "travel_boots": Item("travel_boots", "Сапоги странника", "boots", 25, {"def": 1}, "Прочные кожаные сапоги."),
    "power_ring": Item("power_ring", "Кольцо силы", "ring", 60, {"atk": 2}, "Медное кольцо с руной удара."),
    "mage_ring": Item("mage_ring", "Кольцо мага", "ring", 65, {"mp": 25}, "Сапфировое кольцо, расширяющее запас маны."),
    "guard_amulet": Item("guard_amulet", "Амулет стража", "amulet", 65, {"def": 2, "hp": 15}, "Оберег, усиливающий владельца."),
    "small_bag": Item("small_bag", "Походный рюкзак", "backpack", 35, {"capacity": 6}, "Увеличивает место в инвентаре на 6 слотов."),
    "big_bag": Item("big_bag", "Большой баул", "backpack", 85, {"capacity": 12}, "Вместительный мешок искателя приключений."),
    "gem": Item("gem", "Рубин", "misc", 50, {}, "Драгоценный камень для продажи."),

    # КНИГИ НАВЫКОВ
    "book_whirlwind": Item("book_whirlwind", "Книга: Вихрь клинка", "book", 55, {}, "Активный: круговой удар (Урон: Сила x2, 12 MP).", skill_id="whirlwind"),
    "book_volley": Item("book_volley", "Книга: Залп стрел", "book", 55, {}, "Активный: 3 стрелы веером (Урон: Ловк x1.5, 14 MP).", skill_id="volley"),
    "book_ice": Item("book_ice", "Книга: Ледяная стрела", "book", 60, {}, "Активный: лед (Урон: Инт x2.2 + замедление, 15 MP).", skill_id="ice_bolt"),
    "book_heal": Item("book_heal", "Книга: Исцеление", "book", 50, {}, "Активный: лечение (15 + Инт x3 HP, 18 MP).", skill_id="heal_spell"),
    "book_blade": Item("book_blade", "Книга: Мастер клинка", "book", 65, {}, "Пассивный: +50% от Силы к урону в ближнем бою.", skill_id="passive_blade"),
    "book_skin": Item("book_skin", "Книга: Каменная кожа", "book", 65, {}, "Пассивный: +50% от Стойкости к защите.", skill_id="passive_skin"),
    "book_mana": Item("book_mana", "Книга: Поток маны", "book", 60, {}, "Пассивный: ускоряет регенерацию маны от Интеллекта.", skill_id="passive_mana"),
}
