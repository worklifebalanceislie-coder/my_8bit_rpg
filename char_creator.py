import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_PLAYER
from entities import Entity
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.skills import SkillBook, SKILLS_DB
from components.quests import QuestLog
from components.professions import PROFESSIONS_DB
from items import ITEMS_DB
from appearance import (
    BODY_LAYERS, HEAD_LAYERS, HAIR_LAYERS,
    SKIN_COLORS, HAIR_COLORS, EYE_COLORS, CLOTH_COLORS,
    build_character_sprite, generate_random_appearance
)

RACES = []
CLASSES = []

class CharacterCreator:
    def __init__(self, sprites, db=None):
        self.sprites = sprites
        self.races = db.get_races_from_db() if db else RACES
        self.classes = db.get_classes_from_db() if db else CLASSES

        db_profs = db.get_professions_from_db() if db else list(PROFESSIONS_DB.values())
        self.professions = [None] + db_profs

        self.name = "Герой"
        self.race_idx = 0
        self.class_idx = 0
        self.prof_idx = 0

        self.step = 1           # 1 = Происхождение и Внешность, 2 = Характеристики и Старт
        self.cursor_step1 = 0   # 0: Имя, 1: Раса, 2: Класс, 3: Профессия, 4..10: Внешность, 11: Рандом, 12: Далее
        self.stat_cursor = 0    # 0..4: Статы, 5: Начать игру

        self.bonus_points = 5
        self.allocated = {"str": 0, "agi": 0, "int": 0, "vit": 0, "end": 0}

        # Параметры внешности
        self.body_keys = list(BODY_LAYERS.keys())
        self.head_keys = list(HEAD_LAYERS.keys())
        self.hair_keys = list(HAIR_LAYERS.keys())

        self.app = {
            "body": "tunic",
            "head": "human",
            "hair": "short",
            "skin": 0,
            "hair_color": 0,
            "eye_color": 0,
            "cloth_color": 0,
        }
        self.apply_race_defaults()

        self.font_huge = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 19, bold=True)
        self.font_main = pygame.font.SysFont("consolas", 17)
        self.font_small = pygame.font.SysFont("consolas", 14)

    def apply_race_defaults(self):
        if not self.races:
            return
        r_id = self.races[self.race_idx]["id"]
        if r_id == "elf":
            self.app["head"], self.app["skin"], self.app["hair"] = "elf", 0, "long"
        elif r_id == "goblin":
            self.app["head"], self.app["skin"], self.app["eye_color"] = "goblin", 3, 3
        elif r_id == "skeleton":
            self.app["head"], self.app["skin"], self.app["hair"], self.app["eye_color"] = "skull", 4, "bald", 1
        else:
            self.app["head"], self.app["skin"] = "human", 0

    def sync_bonus_points(self):
        max_pts = 5 if self.professions[self.prof_idx] is None else 4
        while sum(self.allocated.values()) > max_pts:
            for k in reversed(list(self.allocated.keys())):
                if self.allocated[k] > 0:
                    self.allocated[k] -= 1
                    break
        self.bonus_points = max_pts - sum(self.allocated.values())

    def build_player(self):
        race = self.races[self.race_idx]
        cls = self.classes[self.class_idx]
        final_name = self.name.strip() or "Герой"

        spr = build_character_sprite(self.app)
        player = Entity(final_name, 180, 150, COLOR_PLAYER, sprite=spr, faction=race["faction"], sprite_bank=self.sprites)
        player.appearance = dict(self.app)

        player.movement = Movement(player, speed=race["speed"])
        player.inventory = Inventory(capacity=12, gold=cls["gold"] + race["gold_bonus"])
        player.equipment = Equipment()

        st = cls["stats"]
        rb = race["bonuses"]
        al = self.allocated
        player.stats = Stats(
            hp=st["hp"],
            mp=st["mp"],
            str_val=max(1, st["str"] + rb["str"] + al["str"]),
            agi_val=max(1, st["agi"] + rb["agi"] + al["agi"]),
            int_val=max(1, st["int"] + rb["int"] + al["int"]),
            vit_val=max(1, st["vit"] + rb["vit"] + al["vit"]),
            end_val=max(0, st["end"] + rb["end"] + al["end"]),
        )
        player.combat = Combat(player, cooldown=0.45)
        player.skills = SkillBook(player, max_slots=6)
        player.quests = QuestLog(player)
        player.link_components()

        for item_id in cls["items"]:
            if item_id in ITEMS_DB:
                item = ITEMS_DB[item_id]
                player.inventory.add_item(item)
                if item.type in player.equipment.slots and player.equipment.slots[item.type] is None:
                    player.equipment.equip(item, player.inventory)

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
    def cycle_appearance(self, row_idx, delta):
        if row_idx == 4:
            idx = (self.body_keys.index(self.app["body"]) + delta) % len(self.body_keys)
            self.app["body"] = self.body_keys[idx]
        elif row_idx == 5:
            idx = (self.head_keys.index(self.app["head"]) + delta) % len(self.head_keys)
            self.app["head"] = self.head_keys[idx]
        elif row_idx == 6:
            idx = (self.hair_keys.index(self.app["hair"]) + delta) % len(self.hair_keys)
            self.app["hair"] = self.hair_keys[idx]
        elif row_idx == 7:
            self.app["skin"] = (self.app["skin"] + delta) % len(SKIN_COLORS)
        elif row_idx == 8:
            self.app["hair_color"] = (self.app["hair_color"] + delta) % len(HAIR_COLORS)
        elif row_idx == 9:
            self.app["eye_color"] = (self.app["eye_color"] + delta) % len(EYE_COLORS)
        elif row_idx == 10:
            self.app["cloth_color"] = (self.app["cloth_color"] + delta) % len(CLOTH_COLORS)

    def handle_event(self, event):
        # --- УПРАВЛЕНИЕ МЫШЬЮ ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Верхние вкладки (Шаг 1 / Шаг 2)
            if 52 <= my <= 86:
                if 340 <= mx <= 630:
                    self.step = 1
                elif 650 <= mx <= 940:
                    self.step = 2
                return None

            if self.step == 1:
                # Левая колонка: Имя, Раса, Класс, Профессия
                if 40 <= mx <= 620:
                    if 102 <= my <= 177:
                        self.cursor_step1 = 0
                    elif 188 <= my <= 343:
                        self.cursor_step1 = 1
                        delta = -1 if mx < 330 else 1
                        self.race_idx = (self.race_idx + delta) % len(self.races)
                        self.apply_race_defaults()
                    elif 354 <= my <= 489:
                        self.cursor_step1 = 2
                        delta = -1 if mx < 330 else 1
                        self.class_idx = (self.class_idx + delta) % len(self.classes)
                    elif 500 <= my <= 620:
                        self.cursor_step1 = 3
                        delta = -1 if mx < 330 else 1
                        self.prof_idx = (self.prof_idx + delta) % len(self.professions)
                        self.sync_bonus_points()

                # Правая колонка: Кнопка рандома и строки внешности
                elif 650 <= mx <= 1240:
                    if 174 <= my <= 218 and mx >= 810:
                        self.cursor_step1 = 11
                        self.app = generate_random_appearance(self.races[self.race_idx]["id"])
                    else:
                        for row_id in range(4, 11):
                            ry = 270 + (row_id - 4) * 40
                            if ry - 4 <= my <= ry + 28:
                                self.cursor_step1 = row_id
                                delta = -1 if mx < 945 else 1
                                self.cycle_appearance(row_id, delta)
                                break

                # Нижняя кнопка перехода ко 2-му шагу
                if 40 <= mx <= 1240 and 632 <= my <= 676:
                    self.step = 2

            elif self.step == 2:
                # Правая колонка: статы и кнопка старта
                if 650 <= mx <= 1240:
                    stat_keys = ["str", "agi", "int", "vit", "end"]
                    for idx, sk in enumerate(stat_keys):
                        sy = 148 + idx * 84
                        if sy - 6 <= my <= sy + 64:
                            self.stat_cursor = idx
                            if mx < 945 and self.allocated[sk] > 0:
                                self.allocated[sk] -= 1
                                self.bonus_points += 1
                            elif mx >= 945 and self.bonus_points > 0:
                                self.allocated[sk] += 1
                                self.bonus_points -= 1
                            break

                    if 606 <= my <= 676:
                        return self.build_player()

            return None

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_TAB:
            self.step = 2 if self.step == 1 else 1
            return None

        # --- ШАГ 1: ПРОИСХОЖДЕНИЕ И ВНЕШНОСТЬ ---
        if self.step == 1:
            if event.key == pygame.K_UP:
                self.cursor_step1 = (self.cursor_step1 - 1) % 13
                return None
            elif event.key == pygame.K_DOWN:
                self.cursor_step1 = (self.cursor_step1 + 1) % 13
                return None

            # Ввод имени в строке 0 + Буфер обмена Ctrl+C / Ctrl+V / Ctrl+X
            if self.cursor_step1 == 0:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_c:
                        pygame.scrap.put(pygame.SCRAP_TEXT, self.name.encode("utf-8"))
                    elif event.key == pygame.K_x:
                        pygame.scrap.put(pygame.SCRAP_TEXT, self.name.encode("utf-8"))
                        self.name = ""
                    elif event.key == pygame.K_v:
                        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if raw:
                            pasted = raw.decode("utf-8", errors="ignore").replace("\x00", "").strip()
                            self.name = (self.name + pasted)[:16]
                    return None

                if event.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                elif event.key == pygame.K_RETURN:
                    self.cursor_step1 = 1
                elif event.unicode.isprintable() and len(self.name) < 16:
                    self.name += event.unicode
                return None

            if event.key == pygame.K_w:
                self.cursor_step1 = (self.cursor_step1 - 1) % 13
            elif event.key == pygame.K_s:
                self.cursor_step1 = (self.cursor_step1 + 1) % 13
            elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                delta = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
                if self.cursor_step1 == 1:
                    self.race_idx = (self.race_idx + delta) % len(self.races)
                    self.apply_race_defaults()
                elif self.cursor_step1 == 2:
                    self.class_idx = (self.class_idx + delta) % len(self.classes)
                elif self.cursor_step1 == 3:
                    self.prof_idx = (self.prof_idx + delta) % len(self.professions)
                    self.sync_bonus_points()
                elif 4 <= self.cursor_step1 <= 10:
                    self.cycle_appearance(self.cursor_step1, delta)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.cursor_step1 == 11:
                    self.app = generate_random_appearance(self.races[self.race_idx]["id"])
                elif self.cursor_step1 == 12:
                    self.step = 2
                else:
                    self.cursor_step1 = (self.cursor_step1 + 1) % 13

        # --- ШАГ 2: ХАРАКТЕРИСТИКИ И СТАРТ ---
        elif self.step == 2:
            stat_keys = ["str", "agi", "int", "vit", "end"]
            if event.key in (pygame.K_UP, pygame.K_w):
                self.stat_cursor = (self.stat_cursor - 1) % 6
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.stat_cursor = (self.stat_cursor + 1) % 6
            elif self.stat_cursor < 5:
                sk = stat_keys[self.stat_cursor]
                if event.key in (pygame.K_LEFT, pygame.K_a) and self.allocated[sk] > 0:
                    self.allocated[sk] -= 1
                    self.bonus_points += 1
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.bonus_points > 0:
                    self.allocated[sk] += 1
                    self.bonus_points -= 1
            elif self.stat_cursor == 5 and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.build_player()

        return None

    def draw_panel(self, surface, rect, title, is_active):
        pygame.draw.rect(surface, (20, 24, 34), rect, border_radius=6)
        border_col = (240, 195, 75) if is_active else (75, 85, 105)
        pygame.draw.rect(surface, border_col, rect, 2 if is_active else 1, border_radius=6)
        if title:
            lbl = self.font_small.render(title, True, border_col)
            surface.blit(lbl, (rect.x + 12, rect.y + 8))

    def draw(self, surface):
        surface.fill((14, 17, 24))
        header = self.font_huge.render("СОЗДАНИЕ ПЕРСОНАЖА", True, (240, 195, 75))
        surface.blit(header, (WINDOW_WIDTH // 2 - header.get_width() // 2, 12))

        # Верхние вкладки (Шаг 1 / Шаг 2)
        tabs = [(1, "1. ПРОИСХОЖДЕНИЕ И ВНЕШНОСТЬ", 340), (2, "2. ХАРАКТЕРИСТИКИ И СТАРТ", 650)]
        for st_id, t_lbl, tx in tabs:
            t_rect = pygame.Rect(tx, 52, 290, 34)
            active = (self.step == st_id)
            pygame.draw.rect(surface, (45, 58, 82) if active else (24, 28, 38), t_rect, border_radius=6)
            pygame.draw.rect(surface, (240, 195, 75) if active else (80, 90, 110), t_rect, 2, border_radius=6)
            ts = self.font_small.render(t_lbl, True, (255, 255, 255) if active else (170, 180, 195))
            surface.blit(ts, (t_rect.centerx - ts.get_width() // 2, t_rect.centery - ts.get_height() // 2))

        race = self.races[self.race_idx]
        cls = self.classes[self.class_idx]
        pr = self.professions[self.prof_idx]

        # =====================================================================
        # ЭКРАН 1: ПРОИСХОЖДЕНИЕ (СЛЕВА) + КОНСТРУКТОР ВНЕШНОСТИ (СПРАВА)
        # =====================================================================
        if self.step == 1:
            # 1. Имя
            r_name = pygame.Rect(40, 102, 580, 75)
            self.draw_panel(surface, r_name, "ИМЯ ГЕРОЯ", self.cursor_step1 == 0)
            cur = "_" if (self.cursor_step1 == 0 and (pygame.time.get_ticks() // 400) % 2 == 0) else ""
            surface.blit(self.font_title.render(self.name + cur, True, (255, 255, 255)), (r_name.x + 16, r_name.y + 38))

            # 2. Раса
            r_race = pygame.Rect(40, 188, 580, 155)
            self.draw_panel(surface, r_race, "РАСА (< A / D >)", self.cursor_step1 == 1)
            surface.blit(self.font_title.render(f"<  {race['name'].upper()}  >", True, (130, 210, 255)), (r_race.x + 16, r_race.y + 34))
            surface.blit(self.font_small.render(race["desc"], True, (210, 215, 230)), (r_race.x + 16, r_race.y + 64))
            rel_col = (240, 130, 110) if race["faction"] in ("monster", "undead") else (130, 225, 150)
            surface.blit(self.font_small.render(f"Дипломатия: {race['relations']}", True, rel_col), (r_race.x + 16, r_race.y + 90))
            r_sk = SKILLS_DB[race["racial_skill"]].name if race["racial_skill"] in SKILLS_DB else "Нет"
            surface.blit(self.font_small.render(f"Расовый дар: {r_sk}", True, (240, 200, 90)), (r_race.x + 16, r_race.y + 116))

            # 3. Класс
            r_cls = pygame.Rect(40, 354, 580, 135)
            self.draw_panel(surface, r_cls, "КЛАСС (< A / D >)", self.cursor_step1 == 2)
            surface.blit(self.font_title.render(f"<  {cls['name'].upper()}  >", True, (240, 195, 75)), (r_cls.x + 16, r_cls.y + 34))
            surface.blit(self.font_small.render(cls["desc"], True, (210, 215, 230)), (r_cls.x + 16, r_cls.y + 64))
            c_sk = SKILLS_DB[cls["skill"]].name if cls["skill"] in SKILLS_DB else "Нет"
            surface.blit(self.font_small.render(f"Навык: {c_sk}  |  Стартовое золото: {cls['gold'] + race['gold_bonus']}G", True, (160, 200, 240)), (r_cls.x + 16, r_cls.y + 92))

            # 4. Профессия
            r_prof = pygame.Rect(40, 500, 580, 120)
            self.draw_panel(surface, r_prof, "ПРОФЕССИЯ / РЕМЕСЛО (< A / D >)", self.cursor_step1 == 3)
            if pr is None:
                surface.blit(self.font_title.render("<  БЕЗ ПРОФЕССИИ (ВОЛЬНЫЙ)  >", True, (240, 200, 90)), (r_prof.x + 16, r_prof.y + 34))
                surface.blit(self.font_small.render("Бонус: +1 очко статов (5 вместо 4) и +30G! Профессии можно выучить у НПС.", True, (130, 235, 160)), (r_prof.x + 16, r_prof.y + 68))
            else:
                surface.blit(self.font_title.render(f"<  {pr.name.upper()}  >", True, (130, 235, 160)), (r_prof.x + 16, r_prof.y + 34))
                surface.blit(self.font_small.render(pr.desc, True, (210, 215, 230)), (r_prof.x + 16, r_prof.y + 68))

            # Правая половина: Конструктор внешности
            r_app = pygame.Rect(650, 102, 590, 518)
            self.draw_panel(surface, r_app, "КОНСТРУКТОР ВНЕШНОСТИ (< A / D >)", 4 <= self.cursor_step1 <= 11)

            # Крупный предпросмотр спрайта 6x (96x96)
            spr_preview = pygame.transform.scale(build_character_sprite(self.app), (96, 96))
            pygame.draw.rect(surface, (28, 34, 48), (r_app.x + 24, r_app.y + 38, 112, 112), border_radius=8)
            pygame.draw.rect(surface, (100, 115, 140), (r_app.x + 24, r_app.y + 38, 112, 112), 2, border_radius=8)
            surface.blit(spr_preview, (r_app.x + 32, r_app.y + 46))

            skin_name, skin_rgb, _ = SKIN_COLORS[self.app["skin"]]
            hair_name, hair_rgb, _ = HAIR_COLORS[self.app["hair_color"]]
            eye_name, eye_rgb = EYE_COLORS[self.app["eye_color"]]
            cloth_name, cloth_rgb, _ = CLOTH_COLORS[self.app["cloth_color"]]

            app_rows = [
                (4, "Одежда:", BODY_LAYERS[self.app["body"]]["name"], None),
                (5, "Голова:", HEAD_LAYERS[self.app["head"]]["name"], None),
                (6, "Прическа:", HAIR_LAYERS[self.app["hair"]]["name"], None),
                (7, "Цвет кожи:", skin_name, skin_rgb),
                (8, "Цвет волос:", hair_name, hair_rgb),
                (9, "Цвет глаз:", eye_name, eye_rgb),
                (10, "Цвет одежды:", cloth_name, cloth_rgb),
            ]


            for row_id, lbl, val_str, swatch_col in app_rows:
                y = r_app.y + 168 + (row_id - 4) * 40
                is_sel = (self.cursor_step1 == row_id)
                if is_sel:
                    pygame.draw.rect(surface, (45, 58, 82), (r_app.x + 16, y - 4, r_app.width - 32, 32), border_radius=4)
                prefix = "> " if is_sel else "  "
                col = (255, 255, 255) if is_sel else (200, 205, 220)
                surface.blit(self.font_main.render(f"{prefix}{lbl:<14} < {val_str} >", True, col), (r_app.x + 22, y + 2))
                if swatch_col:
                    pygame.draw.rect(surface, swatch_col, (r_app.right - 52, y + 2, 22, 20), border_radius=3)
                    pygame.draw.rect(surface, (255, 255, 255), (r_app.right - 52, y + 2, 22, 20), 1, border_radius=3)

            # Кнопка случайной внешности (row_id = 11)
            rnd_rect = pygame.Rect(r_app.x + 160, r_app.y + 72, 390, 44)
            is_rnd = (self.cursor_step1 == 11)
            pygame.draw.rect(surface, (55, 70, 98) if is_rnd else (32, 38, 52), rnd_rect, border_radius=6)
            pygame.draw.rect(surface, (240, 195, 75) if is_rnd else (90, 100, 120), rnd_rect, 2, border_radius=6)
            r_txt = self.font_main.render("Случайная внешность (Enter)", True, (255, 255, 255))
            surface.blit(r_txt, (rnd_rect.centerx - r_txt.get_width() // 2, rnd_rect.centery - r_txt.get_height() // 2))

            # Кнопка перехода к Шагу 2 (row_id = 12)
            next_rect = pygame.Rect(40, 632, 1200, 44)
            is_next = (self.cursor_step1 == 12)
            pygame.draw.rect(surface, (45, 130, 75) if is_next else (26, 55, 40), next_rect, border_radius=6)
            pygame.draw.rect(surface, (140, 255, 170) if is_next else (70, 130, 90), next_rect, 2, border_radius=6)
            n_txt = self.font_title.render("ДАЛЕЕ: РАСПРЕДЕЛЕНИЕ ХАРАКТЕРИСТИК (Tab / Enter) ➔", True, (255, 255, 255))
            surface.blit(n_txt, (next_rect.centerx - n_txt.get_width() // 2, next_rect.centery - n_txt.get_height() // 2))

        # =====================================================================
        # ЭКРАН 2: ХАРАКТЕРИСТИКИ И ИТОГОВАЯ КАРТОЧКА ГЕРОЯ
        # =====================================================================
        else:
            preview = self.build_player()
            st = preview.stats

            # Левая карточка: Итоговая сводка героя
            card = pygame.Rect(40, 102, 580, 574)
            self.draw_panel(surface, card, "ИТОГОВЫЙ ОБРАЗ ГЕРОЯ", False)
            spr_big = pygame.transform.scale(preview.sprite, (128, 128))
            surface.blit(spr_big, (card.x + 30, card.y + 45))

            prof_name = pr.name if pr else "Без профессии (Вольный)"
            info_lines = [
                (f"Имя: {preview.name}", (255, 255, 255)),
                (f"Раса: {race['name']}", (130, 210, 255)),
                (f"Класс: {cls['name']}", (240, 195, 75)),
                (f"Профессия: {prof_name}", (130, 235, 160)),
                (f"Стартовое золото: {preview.inventory.gold}G", (240, 210, 90)),
            ]
            for idx, (txt, col) in enumerate(info_lines):
                surface.blit(self.font_main.render(txt, True, col), (card.x + 185, card.y + 42 + idx * 28))

            pygame.draw.line(surface, (75, 85, 105), (card.x + 20, card.y + 195), (card.right - 20, card.y + 195), 1)
            combat_lines = [
                f"Здоровье (HP): {st.max_hp}   |   Мана (MP): {st.max_mp}",
                f"Базовый урон: {st.get_atk()}   |   Физическая защита: {st.get_def()}",
                f"Шанс крит. удара: {st.crit_chance}%   |   Скорость бега: {race['speed']}",
                f"Вместимость рюкзака: {preview.inventory.capacity} слотов",
            ]
            for idx, line in enumerate(combat_lines):
                surface.blit(self.font_main.render(line, True, (210, 220, 235)), (card.x + 25, card.y + 215 + idx * 32))

            pygame.draw.line(surface, (75, 85, 105), (card.x + 20, card.y + 355), (card.right - 20, card.y + 355), 1)
            sk_names = ", ".join(s.name for s in preview.skills.learned) or "Нет"
            it_names = ", ".join(i.name for i in preview.inventory.items) or "Пусто"
            surface.blit(self.font_small.render(f"Изученные навыки: {sk_names}", True, (130, 220, 255)), (card.x + 25, card.y + 375))
            surface.blit(self.font_small.render(f"Предметы в сумке: {it_names}", True, (215, 200, 150)), (card.x + 25, card.y + 405))

            # Правая карточка: Распределение статов
            stats_rect = pygame.Rect(650, 102, 590, 490)
            self.draw_panel(surface, stats_rect, f"РАСПРЕДЕЛЕНИЕ ОЧКОВ (ОСТАЛОСЬ: {self.bonus_points})", self.stat_cursor < 5)

            stat_rows = [
                ("str", "Сила (STR)", "Урон в ближнем бою"),
                ("agi", "Ловкость (AGI)", "Урон луком и шанс крита"),
                ("int", "Интеллект (INT)", "Магия, запас и реген MP"),
                ("vit", "Живучесть (VIT)", "Запас и реген здоровья"),
                ("end", "Стойкость (END)", "Общая физическая защита")
            ]

            for idx, (s_key, s_title, s_desc) in enumerate(stat_rows):
                y = stats_rect.y + 46 + idx * 84
                is_sel = (self.stat_cursor == idx)
                if is_sel:
                    pygame.draw.rect(surface, (45, 58, 82), (stats_rect.x + 16, y - 6, stats_rect.width - 32, 70), border_radius=6)

                base_v = cls["stats"][s_key]
                race_v = race["bonuses"][s_key]
                add_v = self.allocated[s_key]
                total_v = base_v + race_v + add_v

                prefix = "> " if is_sel else "  "
                col = (255, 255, 255) if is_sel else (200, 205, 220)
                surface.blit(self.font_title.render(f"{prefix}{s_title}: {total_v}", True, col), (stats_rect.x + 25, y))
                breakdown = f"База: {base_v}  |  Раса: {race_v:+d}  |  Вложено: +{add_v}   (< A / D >)"
                surface.blit(self.font_small.render(breakdown, True, (130, 220, 160)), (stats_rect.x + 42, y + 26))
                surface.blit(self.font_small.render(s_desc, True, (165, 175, 195)), (stats_rect.x + 42, y + 46))

            start_rect = pygame.Rect(650, 606, 590, 70)
            is_start = (self.stat_cursor == 5)
            pygame.draw.rect(surface, (45, 130, 75) if is_start else (26, 55, 40), start_rect, border_radius=8)
            pygame.draw.rect(surface, (140, 255, 170) if is_start else (70, 130, 90), start_rect, 3 if is_start else 2, border_radius=8)
            btn_txt = self.font_huge.render("> НАЧАТЬ ПРИКЛЮЧЕНИЕ <", True, (255, 255, 255) if is_start else (180, 220, 190))
            surface.blit(btn_txt, (start_rect.centerx - btn_txt.get_width() // 2, start_rect.centery - btn_txt.get_height() // 2))

        pygame.draw.rect(surface, (10, 12, 18), (0, WINDOW_HEIGHT - 30, WINDOW_WIDTH, 30))
        hint = "W/S: Выбор строки  |  A/D: Изменить параметр  |  Tab: Переключить вкладку  |  Enter: Подтвердить"
        surface.blit(self.font_small.render(hint, True, (210, 215, 225)), (40, WINDOW_HEIGHT - 23))
