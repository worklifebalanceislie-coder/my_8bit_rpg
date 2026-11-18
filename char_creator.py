import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_PLAYER
from entities import Entity
from items import ITEMS_DB
from factions import FACTION_NAMES_RU
from monster_gen import assemble_monster_sprite
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.skills import SkillBook, SKILLS_DB
from components.quests import QuestLog

RACES = [
    {
        "id": "human",
        "name": "Человек",
        "faction": "player",
        "speed": 80,
        "bonuses": {"str": 1, "agi": 1, "int": 1, "vit": 1, "end": 1},
        "gold_bonus": 15,
        "racial_skill": "race_human",
        "desc": "Сбалансированная раса. Города дружелюбны, гоблины — враги.",
        "relations": "Имперский город: Союзник | Вольный город: Друг | Гоблины: Враги"
    },
    {
        "id": "elf",
        "name": "Лесной Эльф",
        "faction": "player",
        "speed": 88,
        "bonuses": {"str": 0, "agi": 2, "int": 2, "vit": -1, "end": 0},
        "gold_bonus": 10,
        "racial_skill": "race_elf",
        "desc": "Быстрый и ловкий народ. Владеет рывком 'Шаг ветра'.",
        "relations": "Имперский город: Друг | Вольный город: Друг | Гоблины: Враги"
    },
    {
        "id": "goblin",
        "name": "Гоблин",
        "faction": "monster",
        "speed": 90,
        "bonuses": {"str": 1, "agi": 3, "int": -1, "vit": 0, "end": 0},
        "gold_bonus": 0,
        "racial_skill": "race_goblin",
        "desc": "Хитрый дикарь. Гоблины считают вас своим! Империя — враг.",
        "relations": "Гоблины: СВОИ | Вольный город: Нейтрал | Имперский город: ВРАГИ!"
    },
    {
        "id": "skeleton",
        "name": "Скелет (Нежить)",
        "faction": "undead",
        "speed": 75,
        "bonuses": {"str": 0, "agi": 0, "int": 2, "vit": -1, "end": 2},
        "gold_bonus": 0,
        "racial_skill": "race_skeleton",
        "desc": "Восставший мертвец. Похищает жизнь врагов. Все живые опасаются вас.",
        "relations": "Вольный город: Нейтрал | Имперский город: ВРАГИ | Гоблины: ВРАГИ"
    }
]

CLASSES = [
    {
        "id": "warrior",
        "name": "Воин",
        "desc": "Мастер ближнего боя с высокой силой и здоровьем.",
        "stats": {"hp": 75, "mp": 25, "str": 5, "agi": 2, "int": 1, "vit": 4, "end": 2},
        "gold": 50,
        "items": ["rusty_sword", "leather_armor", "potion"],
        "skill": "whirlwind"
    },
    {
        "id": "ranger",
        "name": "Следопыт",
        "desc": "Меткий стрелок с высоким шансом критического удара.",
        "stats": {"hp": 60, "mp": 35, "str": 2, "agi": 5, "int": 2, "vit": 3, "end": 1},
        "gold": 60,
        "items": ["hunting_bow", "travel_boots", "potion"],
        "skill": "volley"
    },
    {
        "id": "mage",
        "name": "Чародей",
        "desc": "Повелитель стихий с большим запасом и регеном маны.",
        "stats": {"hp": 50, "mp": 55, "str": 1, "agi": 2, "int": 5, "vit": 2, "end": 1},
        "gold": 55,
        "items": ["fire_staff", "mana_potion", "potion"],
        "skill": "ice_bolt"
    },
    {
        "id": "wanderer",
        "name": "Странник",
        "desc": "Универсальный искатель приключений с походным рюкзаком.",
        "stats": {"hp": 65, "mp": 35, "str": 3, "agi": 3, "int": 3, "vit": 3, "end": 2},
        "gold": 95,
        "items": ["rusty_sword", "small_bag", "potion"],
        "skill": "heal_spell"
    }
]

STAT_ROWS = [
    ("str", "Сила (STR)", "Урон в ближнем бою"),
    ("agi", "Ловкость (AGI)", "Урон луком и шанс крита"),
    ("int", "Интеллект (INT)", "Магия, запас и реген MP"),
    ("vit", "Живучесть (VIT)", "Макс. HP и реген здоровья"),
    ("end", "Стойкость (END)", "Общая физическая защита")
]

class CharacterCreator:
    def __init__(self, sprites, db=None):
        self.sprites = sprites
        self.races = db.get_races_from_db() if db else RACES
        self.classes = db.get_classes_from_db() if db else CLASSES
        self.name = "Герой"
        self.race_idx = 0
        self.class_idx = 0
        self.section = "race"  # 'name', 'race', 'class', 'stats', 'start'
        self.stat_cursor = 0
        self.bonus_points = 4
        self.allocated = {"str": 0, "agi": 0, "int": 0, "vit": 0, "end": 0}

        # Спрайт для расы Скелет собираем из наших запчастей
        self.skeleton_sprite = assemble_monster_sprite(["body_ribcage", "head_skull"], (220, 215, 200), (155, 150, 135), (80, 210, 255))

        self.font_huge = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_main = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 15)

    def get_race_sprite(self, race):
        s_key = race.get("sprite_key")
        if s_key and s_key in self.sprites:
            return self.sprites[s_key]
        if race["id"] == "goblin":
            return self.sprites["goblin"]
        elif race["id"] == "skeleton":
            return self.skeleton_sprite
        elif race["id"] == "elf":
            return self.sprites["adventurer"]
        return self.sprites["player"]

    def reset_points(self):
        self.bonus_points = 4
        self.allocated = {"str": 0, "agi": 0, "int": 0, "vit": 0, "end": 0}

    def build_player(self):
        race = self.races[self.race_idx]
        cls = cls = self.classes[self.class_idx]
        base = cls["stats"]
        r_bon = race["bonuses"]
        final_name = self.name.strip() or race["name"]

        spr = self.get_race_sprite(race)
        player = Entity(final_name, 180, 150, COLOR_PLAYER, sprite=spr, faction=race["faction"], sprite_bank=self.sprites)
        player.sprite_key = race.get("sprite_key")

        player = Entity(final_name, 180, 150, COLOR_PLAYER, sprite=spr, faction=race["faction"], sprite_bank=self.sprites)
        player.movement = Movement(player, speed=race["speed"])
        player.inventory = Inventory(capacity=4, gold=cls["gold"] + race["gold_bonus"])
        player.equipment = Equipment()
        player.stats = Stats(
            hp=base["hp"],
            mp=base["mp"],
            str_val=max(1, base["str"] + r_bon["str"] + self.allocated["str"]),
            agi_val=max(1, base["agi"] + r_bon["agi"] + self.allocated["agi"]),
            int_val=max(1, base["int"] + r_bon["int"] + self.allocated["int"]),
            vit_val=max(1, base["vit"] + r_bon["vit"] + self.allocated["vit"]),
            end_val=max(0, base["end"] + r_bon["end"] + self.allocated["end"])
        )
        player.combat = Combat(player, cooldown=0.4)
        player.skills = SkillBook(player, max_slots=4)
        player.quests = QuestLog(player)
        player.link_components()

        for item_id in cls["items"]:
            item = ITEMS_DB[item_id]
            player.inventory.add_item(item)
            if item.type in player.equipment.slots:
                player.equipment.equip(item, player.inventory)

        # Изучаем расовый навык + классовый навык
        if race["racial_skill"]:
            player.skills.learn_skill(race["racial_skill"])
        if cls["skill"]:
            player.skills.learn_skill(cls["skill"])

        return player
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None

        sections = ["name", "race", "class", "stats", "start"]
        cur_idx = sections.index(self.section)

        if event.key == pygame.K_TAB:
            self.section = sections[(cur_idx + 1) % len(sections)]
            return None

        if self.section == "name":
            if event.key in (pygame.K_DOWN, pygame.K_RETURN):
                self.section = "race"
            elif event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif len(self.name) < 14 and event.unicode.isprintable() and event.unicode != " ":
                self.name += event.unicode

        elif self.section == "race":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.section = "name"
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RETURN):
                self.section = "class"
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.race_idx = (self.race_idx - 1) % len(self.races)
                self.reset_points()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.race_idx = (self.race_idx + 1) % len(self.races)
                self.reset_points()

        elif self.section == "class":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.section = "race"
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RETURN):
                self.section = "stats"
                self.stat_cursor = 0
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.class_idx = (self.class_idx - 1) % len(self.classes)
                self.reset_points()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.class_idx = (self.class_idx + 1) % len(self.classes)
                self.reset_points()

        elif self.section == "stats":
            if event.key in (pygame.K_UP, pygame.K_w):
                if self.stat_cursor > 0:
                    self.stat_cursor -= 1
                else:
                    self.section = "class"
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if self.stat_cursor < len(STAT_ROWS) - 1:
                    self.stat_cursor += 1
                else:
                    self.section = "start"
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_PLUS, pygame.K_EQUALS):
                key, _, _ = STAT_ROWS[self.stat_cursor]
                if self.bonus_points > 0:
                    self.allocated[key] += 1
                    self.bonus_points -= 1
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_MINUS):
                key, _, _ = STAT_ROWS[self.stat_cursor]
                if self.allocated[key] > 0:
                    self.allocated[key] -= 1
                    self.bonus_points += 1


        elif self.section == "start":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.section = "stats"
                self.stat_cursor = len(STAT_ROWS) - 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.build_player()

        return None

    def draw_panel(self, surface, rect, title, active):
        pygame.draw.rect(surface, (22, 26, 36), rect, border_radius=6)
        col = (240, 195, 75) if active else (85, 95, 115)
        pygame.draw.rect(surface, col, rect, 2, border_radius=6)
        surface.blit(self.font_title.render(title, True, col), (rect.x + 14, rect.y + 8))
        pygame.draw.line(surface, col, (rect.x + 10, rect.y + 36), (rect.right - 10, rect.y + 36), 2)

    def draw(self, surface):
        surface.fill((14, 17, 24))
        title = self.font_huge.render("СОЗДАНИЕ ПЕРСОНАЖА", True, (240, 195, 75))
        surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 14))

        # 1. Имя
        name_rect = pygame.Rect(40, 58, 580, 76)
        self.draw_panel(surface, name_rect, "1. ИМЯ ГЕРОЯ", self.section == "name")
        cur = "_" if (self.section == "name" and (pygame.time.get_ticks() // 400) % 2 == 0) else ""
        surface.blit(self.font_title.render(f"  {self.name}{cur}", True, (255, 255, 255)), (name_rect.x + 14, name_rect.y + 42))

        # 2. Раса и дипломатия
        race_rect = pygame.Rect(40, 144, 580, 165)
        race = self.races[self.race_idx]
        self.draw_panel(surface, race_rect, "2. ВЫБОР РАСЫ (◀ A / D ▶)", self.section == "race")
        surface.blit(self.font_title.render(f"◀  {race['name'].upper()}  ▶", True, (255, 185, 90)), (race_rect.x + 16, race_rect.y + 44))
        surface.blit(self.font_small.render(race["desc"], True, (210, 215, 230)), (race_rect.x + 16, race_rect.y + 72))
        r_sk = SKILLS_DB[race["racial_skill"]]
        surface.blit(self.font_small.render(f"Расовый навык: {r_sk.name} — {r_sk.desc}", True, (130, 230, 160)), (race_rect.x + 16, race_rect.y + 98))
        surface.blit(self.font_small.render(race["relations"], True, (150, 200, 255)), (race_rect.x + 16, race_rect.y + 124))

        # 3. Класс
        cls_rect = pygame.Rect(40, 319, 580, 145)
        cls = self.classes[self.class_idx]
        self.draw_panel(surface, cls_rect, "3. ВЫБОР КЛАССА (◀ A / D ▶)", self.section == "class")
        surface.blit(self.font_title.render(f"◀  {cls['name'].upper()}  ▶", True, (120, 220, 255)), (cls_rect.x + 16, cls_rect.y + 44))
        surface.blit(self.font_small.render(cls["desc"], True, (210, 215, 230)), (cls_rect.x + 16, cls_rect.y + 72))
        gear_names = [ITEMS_DB[i].name for i in cls["items"]]
        surface.blit(self.font_small.render(f"Снаряжение: {', '.join(gear_names)}  |  Золото: {cls['gold'] + race['gold_bonus']}G", True, (240, 200, 80)), (cls_rect.x + 16, cls_rect.y + 100))

        # 4. Превью
        prev_rect = pygame.Rect(40, 474, 580, 195)
        self.draw_panel(surface, prev_rect, "ПРЕДПРОСМОТР ГЕРОЯ", False)
        preview = self.build_player()
        big_spr = pygame.transform.scale(preview.build_animated_sprite(), (110, 100))
        surface.blit(big_spr, (prev_rect.x + 25, prev_rect.y + 55))

        st = preview.stats
        sk_names = ", ".join(s.name for s in preview.skills.learned)
        p_lines = [
            f"Фракция: {FACTION_NAMES_RU.get(preview.faction, preview.faction)}",
            f"HP: {st.max_hp} (+{st.hp_regen}/с)   |   MP: {st.max_mp} (+{st.mp_regen}/с)",
            f"Защита: {st.get_def()}   |   Крит: {st.crit_chance}%   |   Скорость: {race['speed']}",
            f"Навыки: {sk_names}"
        ]
        for i, line in enumerate(p_lines):
            surface.blit(self.font_small.render(line, True, (215, 225, 240)), (prev_rect.x + 155, prev_rect.y + 48 + i * 32))

        # 5. Характеристики (справа)
        stat_rect = pygame.Rect(640, 58, 600, 515)
        self.draw_panel(surface, stat_rect, f"4. ХАРАКТЕРИСТИКИ (Очков: {self.bonus_points})", self.section == "stats")

        for idx, (key, title_ru, desc_ru) in enumerate(STAT_ROWS):
            y = stat_rect.y + 48 + idx * 90
            is_sel = (self.section == "stats" and self.stat_cursor == idx)
            if is_sel:
                pygame.draw.rect(surface, (45, 55, 75), (stat_rect.x + 12, y - 4, stat_rect.width - 24, 76), border_radius=4)

            total_val = max(0 if key == "end" else 1, cls["stats"][key] + race["bonuses"][key] + self.allocated[key])
            r_mod = race["bonuses"][key]
            r_str = f" (раса {r_mod:+d})" if r_mod != 0 else ""
            a_str = f" (+{self.allocated[key]})" if self.allocated[key] > 0 else ""

            col = (255, 255, 255) if is_sel else (200, 205, 220)
            surface.blit(self.font_title.render(f"{'▶ ' if is_sel else '  '}{title_ru}:  [ {total_val} ]{r_str}{a_str}", True, col), (stat_rect.x + 18, y))
            surface.blit(self.font_small.render(f"   {desc_ru}  (◀ A: -1 / D: +1 ▶)", True, (150, 175, 205)), (stat_rect.x + 18, y + 34))

        # 6. Кнопка старта
        btn_rect = pygame.Rect(640, 585, 600, 84)
        btn_col = (60, 160, 90) if self.section == "start" else (35, 65, 50)
        pygame.draw.rect(surface, btn_col, btn_rect, border_radius=6)
        border_c = (240, 195, 75) if self.section == "start" else (90, 130, 105)
        pygame.draw.rect(surface, border_c, btn_rect, 2, border_radius=6)
        btn_txt = self.font_title.render("▶  НАЧАТЬ ПРИКЛЮЧЕНИЕ (ENTER)  ◀", True, (255, 255, 255))
        surface.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width() // 2, btn_rect.centery - btn_txt.get_height() // 2))

        pygame.draw.rect(surface, (10, 12, 18), (0, WINDOW_HEIGHT - 32, WINDOW_WIDTH, 32))
        hint = "W/S или TAB: Переход по пунктам  |  A/D: Сменить расу, класс или очки  |  Enter: Старт"
        surface.blit(self.font_small.render(hint, True, (220, 220, 220)), (40, WINDOW_HEIGHT - 24))
