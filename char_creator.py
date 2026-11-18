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
        from components.professions import PROFESSIONS_DB
        db_profs = db.get_professions_from_db() if db else list(PROFESSIONS_DB.values())
        self.professions = [None] + db_profs
        self.prof_idx = 0

    def sync_bonus_points(self):
        max_pts = 5 if self.professions[self.prof_idx] is None else 4
        while sum(self.allocated.values()) > max_pts:
            for k in reversed(list(self.allocated.keys())):
                if self.allocated[k] > 0:
                    self.allocated[k] -= 1
                    break
        self.bonus_points = max_pts - sum(self.allocated.values())

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

        chosen_prof = self.professions[self.prof_idx] if self.professions else None
        if chosen_prof is None:
            player.inventory.gold += 30
        else:
            player.professions.learn(chosen_prof.id, level=1)
            starter_mats = {
                "blacksmith": ["iron_ore", "iron_ore", "wood_log"],
                "carpenter": ["wood_log", "wood_log", "leather_piece"],
                "alchemist": ["herb_leaf", "herb_leaf"],
                "merchant": ["gem"]
            }
            for mat_id in starter_mats.get(chosen_prof.id, []):
                if mat_id in ITEMS_DB:
                    player.inventory.add_item(ITEMS_DB[mat_id])

        return player

    
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None

        sections = ["name", "race", "class", "prof", "stats", "start"]
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
                self.section = "prof"
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.class_idx = (self.class_idx - 1) % len(self.classes)
                self.reset_points()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.class_idx = (self.class_idx + 1) % len(self.classes)
                self.reset_points()

        elif self.section == "prof":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.section = "class"
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RETURN):
                self.section = "stats"
                self.stat_cursor = 0
            elif event.key in (pygame.K_LEFT, pygame.K_a) and self.professions:
                self.prof_idx = (self.prof_idx - 1) % len(self.professions)
                self.sync_bonus_points()
            elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.professions:
                self.prof_idx = (self.prof_idx + 1) % len(self.professions)
                self.sync_bonus_points()

        elif self.section == "stats":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.section = "prof"
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
        header = self.font_huge.render("СОЗДАНИЕ ПЕРСОНАЖА", True, (240, 195, 75))
        surface.blit(header, (WINDOW_WIDTH // 2 - header.get_width() // 2, 12))

        # --- ЛЕВАЯ КОЛОНКА (5 аккуратных блоков без наложения) ---
        # 1. Имя (y: 52..117)
        name_rect = pygame.Rect(40, 52, 580, 65)
        self.draw_panel(surface, name_rect, "1. ИМЯ ГЕРОЯ", self.section == "name")
        cursor_char = "_" if (self.section == "name" and (pygame.time.get_ticks() // 400) % 2 == 0) else ""
        disp_name = self.name + cursor_char
        surface.blit(self.font_title.render(disp_name, True, (255, 255, 255)), (name_rect.x + 18, name_rect.y + 34))

        # 2. Раса (y: 125..265)
        race = self.races[self.race_idx]
        race_rect = pygame.Rect(40, 125, 580, 140)
        self.draw_panel(surface, race_rect, "2. ВЫБОР РАСЫ (◀ A / D ▶)", self.section == "race")
        surface.blit(self.font_title.render(f"◀  {race['name'].upper()}  ▶", True, (130, 210, 255)), (race_rect.x + 18, race_rect.y + 36))
        surface.blit(self.font_small.render(race["desc"], True, (210, 215, 230)), (race_rect.x + 18, race_rect.y + 64))
        rel_col = (240, 130, 110) if race["faction"] in ("monster", "undead") else (130, 225, 150)
        surface.blit(self.font_small.render(f"Дипломатия: {race['relations']}", True, rel_col), (race_rect.x + 18, race_rect.y + 86))
        r_skill_name = SKILLS_DB[race["racial_skill"]].name if race["racial_skill"] in SKILLS_DB else "Нет"
        surface.blit(self.font_small.render(f"Расовый дар: {r_skill_name}", True, (240, 200, 90)), (race_rect.x + 18, race_rect.y + 108))

        # 3. Класс (y: 273..393)
        cls = self.classes[self.class_idx]
        cls_rect = pygame.Rect(40, 273, 580, 120)
        self.draw_panel(surface, cls_rect, "3. ВЫБОР КЛАССА (◀ A / D ▶)", self.section == "class")
        surface.blit(self.font_title.render(f"◀  {cls['name'].upper()}  ▶", True, (240, 195, 75)), (cls_rect.x + 18, cls_rect.y + 36))
        surface.blit(self.font_small.render(cls["desc"], True, (210, 215, 230)), (cls_rect.x + 18, cls_rect.y + 64))
        c_skill_name = SKILLS_DB[cls["skill"]].name if cls["skill"] in SKILLS_DB else "Нет"
        surface.blit(self.font_small.render(f"Навык: {c_skill_name}  |  Золото: {cls['gold'] + race['gold_bonus']}G", True, (160, 200, 240)), (cls_rect.x + 18, cls_rect.y + 88))

        # 4. Профессия (y: 401..496)
        prof_rect = pygame.Rect(40, 401, 580, 95)
        self.draw_panel(surface, prof_rect, "4. ПРОФЕССИЯ / РЕМЕСЛО (◀ A / D ▶)", self.section == "prof")
        pr = self.professions[self.prof_idx] if self.professions else None
        if pr is None:
            surface.blit(self.font_title.render("◀  БЕЗ ПРОФЕССИИ (ВОЛЬНЫЙ ГЕРОЙ)  ▶", True, (240, 200, 90)), (prof_rect.x + 18, prof_rect.y + 36))
            surface.blit(self.font_small.render("Бонус за свободу: +1 очко характеристик (5 вместо 4) и +30G!", True, (130, 235, 160)), (prof_rect.x + 18, prof_rect.y + 64))
        else:
            surface.blit(self.font_title.render(f"◀  {pr.name.upper()}  ▶", True, (130, 235, 160)), (prof_rect.x + 18, prof_rect.y + 36))
            surface.blit(self.font_small.render(pr.desc, True, (210, 215, 230)), (prof_rect.x + 18, prof_rect.y + 64))


        # 5. Предпросмотр персонажа (y: 504..674)
        prev_rect = pygame.Rect(40, 504, 580, 170)
        self.draw_panel(surface, prev_rect, "ПРЕДПРОСМОТР ГЕРОЯ", False)
        preview = self.build_player()
        spr_big = pygame.transform.scale(preview.sprite, (96, 96))
        surface.blit(spr_big, (prev_rect.x + 28, prev_rect.y + 46))

        st = preview.stats
        surface.blit(self.font_main.render(f"Имя: {preview.name} ({race['name']})", True, (255, 255, 255)), (prev_rect.x + 150, prev_rect.y + 42))
        surface.blit(self.font_main.render(f"Здоровье (HP): {st.max_hp}   |   Мана (MP): {st.max_mp}", True, (120, 230, 150)), (prev_rect.x + 150, prev_rect.y + 72))
        surface.blit(self.font_main.render(f"Урон: {st.get_atk()}   |   Защита: {st.get_def()}   |   Крит: {st.crit_chance}%", True, (240, 195, 75)), (prev_rect.x + 150, prev_rect.y + 102))
        surface.blit(self.font_small.render(f"Скорость: {race['speed']}   |   Слоты рюкзака: {preview.inventory.capacity}", True, (180, 195, 220)), (prev_rect.x + 150, prev_rect.y + 132))

        # --- ПРАВАЯ КОЛОНКА (Характеристики + Кнопка старта) ---
        stats_rect = pygame.Rect(650, 52, 590, 540)
        self.draw_panel(surface, stats_rect, f"5. ХАРАКТЕРИСТИКИ (Очков: {self.bonus_points})", self.section == "stats")

        stat_rows = [
            ("str", "Сила (STR)", "Урон в ближнем бою"),
            ("agi", "Ловкость (AGI)", "Урон луком и шанс крита"),
            ("int", "Интеллект (INT)", "Магия, запас и реген MP"),
            ("vit", "Живучесть (VIT)", "Запас и реген здоровья"),
            ("end", "Стойкость (END)", "Общая физическая защита")
        ]

        for idx, (s_key, s_title, s_desc) in enumerate(stat_rows):
            y = stats_rect.y + 52 + idx * 88
            is_sel = (self.section == "stats" and self.stat_cursor == idx)
            if is_sel:
                pygame.draw.rect(surface, (45, 58, 82), (stats_rect.x + 16, y - 6, stats_rect.width - 32, 74), border_radius=6)

            base_v = cls["stats"][s_key]
            race_v = race["bonuses"][s_key]
            add_v = self.allocated[s_key]
            total_v = base_v + race_v + add_v

            prefix = "▶ " if is_sel else "  "
            col = (255, 255, 255) if is_sel else (200, 205, 220)
            surface.blit(self.font_title.render(f"{prefix}{s_title}: {total_v}", True, col), (stats_rect.x + 25, y))

            breakdown = f"База: {base_v}  |  Раса: {race_v:+d}  |  Вложено: +{add_v}   (◀ A / D ▶)"
            surface.blit(self.font_small.render(breakdown, True, (130, 220, 160)), (stats_rect.x + 42, y + 28))
            surface.blit(self.font_small.render(s_desc, True, (165, 175, 195)), (stats_rect.x + 42, y + 48))

        # Кнопка старта в правом нижнем углу (y: 604..674)
        start_rect = pygame.Rect(650, 604, 590, 70)
        is_start = (self.section == "start")
        bg_col = (45, 130, 75) if is_start else (26, 55, 40)
        border_col = (140, 255, 170) if is_start else (70, 130, 90)
        pygame.draw.rect(surface, bg_col, start_rect, border_radius=8)
        pygame.draw.rect(surface, border_col, start_rect, 3 if is_start else 2, border_radius=8)

        btn_txt = self.font_huge.render("▶ НАЧАТЬ ПРИКЛЮЧЕНИЕ ◀", True, (255, 255, 255) if is_start else (180, 220, 190))
        surface.blit(btn_txt, (start_rect.centerx - btn_txt.get_width() // 2, start_rect.centery - btn_txt.get_height() // 2))

        pygame.draw.rect(surface, (10, 12, 18), (0, WINDOW_HEIGHT - 32, WINDOW_WIDTH, 32))
        hint = "W/S: Переход по блокам  |  A/D: Изменить выбор  |  Enter: Начать игру"
        surface.blit(self.font_small.render(hint, True, (210, 215, 225)), (40, WINDOW_HEIGHT - 24))
