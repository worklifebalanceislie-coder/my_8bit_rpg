import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT
from components.trade import Trade

SLOT_NAMES_RU = {
    "weapon": "Оружие",
    "armor": "Броня",
    "pants": "Штаны",
    "boots": "Сапоги",
    "ring": "Кольцо",
    "amulet": "Амулет",
    "backpack": "Рюкзак"
}

TYPE_NAMES_RU = {
    "weapon": "Оружие",
    "armor": "Нагрудник",
    "pants": "Штаны",
    "boots": "Сапоги",
    "ring": "Кольцо",
    "amulet": "Амулет",
    "backpack": "Сумка",
    "consumable": "Расходник",
    "misc": "Ценность",
    "book": "Книга навыка"
}


class UIManager:
    def __init__(self, player):
        self.player = player
        self.is_open = False
        self.mode = None          # 'inventory', 'chest', 'trade'
        self.target = None
        self.active_side = "left" # 'left' или 'right'
        self.cursor = 0
        self.font_title = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_main = pygame.font.SysFont("consolas", 20)
        self.font_small = pygame.font.SysFont("consolas", 18)

    def open_inventory(self):
        self.is_open = True
        self.mode = "inventory"
        self.target = None
        self.active_side = "left"
        self.cursor = 0

    def open_stats(self):
        self.is_open = True
        self.mode = "stats"
        self.target = None
        self.active_side = "left"
        self.cursor = 0

    def open_skills(self):
        self.is_open = True
        self.mode = "skills"
        self.target = None
        self.active_side = "left"
        self.cursor = 0

    def open_container(self, target, mode):
        self.is_open = True
        self.mode = mode
        self.target = target
        self.active_side = "right"
        self.cursor = 0
        if mode == "chest" and target.inventory and target.inventory.gold > 0:
            self.player.inventory.gold += target.inventory.gold
            target.inventory.gold = 0

    def close(self):
        self.is_open = False
        self.mode = None
        self.target = None

    def get_current_list_len(self):
        if self.mode == "stats":
            return 5
        if self.active_side == "left":
            return len(self.player.inventory.items)
        if self.mode == "inventory":
            return len(self.player.equipment.slots)
        if self.target and self.target.inventory:
            return len(self.target.inventory.items)
        if self.mode == "skills":
            return len(self.player.skills.learned) if self.player.skills else 0
        return 0

    def get_selected_item(self):
        """Возвращает объект Item под курсором для отображения его характеристик"""
        if self.active_side == "left":
            items = self.player.inventory.items
            if 0 <= self.cursor < len(items):
                return items[self.cursor]
        else:
            if self.mode == "inventory":
                keys = list(self.player.equipment.slots.keys())
                if 0 <= self.cursor < len(keys):
                    return self.player.equipment.slots[keys[self.cursor]]
            elif self.target and self.target.inventory:
                items = self.target.inventory.items
                if 0 <= self.cursor < len(items):
                    return items[self.cursor]
        return None

    def handle_input(self, event):
        if not self.is_open or event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_TAB, pygame.K_c, pygame.K_k):
            self.close()
            return "Окно закрыто"


        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.active_side = "left"
            self.cursor = 0
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.active_side = "right"
            self.cursor = 0

        max_len = self.get_current_list_len()
        if event.key in (pygame.K_UP, pygame.K_w) and max_len > 0:
            self.cursor = (self.cursor - 1) % max_len
        elif event.key in (pygame.K_DOWN, pygame.K_s) and max_len > 0:
            self.cursor = (self.cursor + 1) % max_len

        if event.key in (pygame.K_RETURN, pygame.K_e):
            return self.perform_action()

        return None
    def perform_action(self):
        if self.mode == "inventory":
            if self.active_side == "left":
                items = self.player.inventory.items
                if not items or self.cursor >= len(items):
                    return None
                item = items[self.cursor]
                if item.type in self.player.equipment.slots:
                    self.player.equipment.equip(item, self.player.inventory)
                    self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return f"Надето: {item.name}"
                elif item.type == "consumable":
                    if "heal" in item.stats_bonus:
                        heal = item.stats_bonus["heal"]
                        self.player.stats.hp = min(float(self.player.stats.max_hp), self.player.stats.hp + heal)
                        self.player.inventory.remove_item(item)
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                        return f"Выпито: {item.name} (+{heal} HP)"
                    elif "mana" in item.stats_bonus:
                        mana = item.stats_bonus["mana"]
                        self.player.stats.mp = min(float(self.player.stats.max_mp), self.player.stats.mp + mana)
                        self.player.inventory.remove_item(item)
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                        return f"Выпито: {item.name} (+{mana} MP)"

                elif item.type == "book" and item.skill_id and self.player.skills:
                    ok, msg = self.player.skills.learn_skill(item.skill_id)
                    if ok:
                        self.player.inventory.remove_item(item)
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return msg

                return f"{item.name}: нельзя использовать"

            elif self.active_side == "right":
                slot_keys = list(self.player.equipment.slots.keys())
                slot_name = slot_keys[self.cursor]
                if self.player.equipment.slots[slot_name]:
                    item_name = self.player.equipment.slots[slot_name].name
                    if self.player.equipment.unequip(slot_name, self.player.inventory):
                        return f"Снято: {item_name}"
                    return "Рюкзак полон!"

        elif self.mode == "chest" and self.target:
            src = self.target.inventory if self.active_side == "right" else self.player.inventory
            dst = self.player.inventory if self.active_side == "right" else self.target.inventory
            word = "Взято" if self.active_side == "right" else "Положено"
            if src.items and self.cursor < len(src.items):
                item = src.items[self.cursor]
                if src.transfer_to(dst, item):
                    self.cursor = max(0, min(self.cursor, len(src.items) - 1))
                    return f"{word}: {item.name}"
                return "Нет свободного места!"

        elif self.mode == "skills" and self.player.skills:
            ok, msg = self.player.skills.forget_skill(self.cursor)
            if ok:
                self.cursor = max(0, min(self.cursor, len(self.player.skills.learned) - 1))
                return msg


        elif self.mode == "trade" and self.target:
            if self.active_side == "right":
                items = self.target.inventory.items
                if items and self.cursor < len(items):
                    item = items[self.cursor]
                    ok, msg = Trade.buy_item(self.player.inventory, self.target.inventory, item)
                    self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return msg
            elif self.active_side == "left":
                items = self.player.inventory.items
                if items and self.cursor < len(items):
                    item = items[self.cursor]
                    ok, msg = Trade.sell_item(self.player.inventory, self.target.inventory, item)
                    self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return msg
        elif self.mode == "stats":
            stat_keys = ["str", "agi", "int", "vit", "end"]
            stat_names = ["Сила", "Ловкость", "Интеллект", "Живучесть", "Стойкость"]
            chosen = stat_keys[self.cursor]
            if self.player.stats.upgrade_stat(chosen):
                return f"Улучшено: {stat_names[self.cursor]} (+1)"
            return "Нет свободных очков характеристик!"


        return None

    def draw_box(self, surface, rect, title, is_active):
        pygame.draw.rect(surface, (20, 24, 34), rect, border_radius=4)
        border_color = (240, 195, 75) if is_active else (95, 105, 125)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=4)
        title_surf = self.font_title.render(title, True, border_color)
        surface.blit(title_surf, (rect.x + 16, rect.y + 12))
        pygame.draw.line(surface, border_color, (rect.x + 10, rect.y + 44), (rect.right - 10, rect.y + 44), 2)

    def draw_item_list(self, surface, rect, items, side, price_mode=None):
        if not items:
            empty_surf = self.font_main.render("(пусто)", True, (130, 135, 150))
            surface.blit(empty_surf, (rect.x + 20, rect.y + 60))
            return
        for idx, item in enumerate(items):
            y = rect.y + 56 + idx * 32
            is_sel = (self.active_side == side and self.cursor == idx)
            if is_sel:
                pygame.draw.rect(surface, (45, 55, 75), (rect.x + 10, y - 4, rect.width - 20, 28), border_radius=3)
            prefix = "▶ " if is_sel else "  "
            color = (255, 255, 255) if is_sel else (200, 205, 220)
            label = f"{prefix}{item.name}"
            if price_mode == "buy":
                label = f"{prefix}{item.name}  [{item.value}G]"
            elif price_mode == "sell":
                label = f"{prefix}{item.name}  [{max(1, item.value // 2)}G]"
            txt = self.font_main.render(label, True, color)
            surface.blit(txt, (rect.x + 16, y))

    def draw(self, surface):
        if not self.is_open:
            return

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))

        if self.mode == "stats":
            box_rect = pygame.Rect(290, 60, 700, 560)
            st = self.player.stats
            self.draw_box(surface, box_rect, f"ПРОКАЧКА  |  Уровень: {st.level}  |  Очков: {st.stat_points}", True)

            options = [
                ("Сила (STR)", f"Текущее: {st.str}  (Урон в ближнем бою: {st.get_atk('melee')})", "+1 урон мечом"),
                ("Ловкость (AGI)", f"Текущее: {st.agi}  (Урон луком: {st.get_atk('bow')}, Крит: {st.crit_chance}%)", "+1 урон луком, +3% крит"),
                ("Интеллект (INT)", f"Текущее: {st.int}  (Магия: {st.get_atk('staff')}, MP: {st.max_mp}, Реген: {st.mp_regen}/с)", "+1 магия, +10 MP, +0.5/с реген"),
                ("Живучесть (VIT)", f"Текущее: {st.vit}  (Макс. HP: {st.max_hp}, Реген: {st.hp_regen}/с)", "+10 HP, +0.35/с реген"),
                ("Стойкость (END)", f"Текущее: {st.end}  (Общая защита: {st.get_def()})", "+1 защита")
            ]

            for idx, (title, cur_val, bonus_txt) in enumerate(options):
                y = box_rect.y + 62 + idx * 78
                is_sel = (self.cursor == idx)
                if is_sel:
                    pygame.draw.rect(surface, (45, 55, 75), (box_rect.x + 15, y - 6, box_rect.width - 30, 66), border_radius=4)
                prefix = "▶ " if is_sel else "  "
                color = (255, 255, 255) if is_sel else (200, 205, 220)
                surface.blit(self.font_title.render(f"{prefix}{title}", True, color), (box_rect.x + 25, y))
                surface.blit(self.font_small.render(f"  {cur_val}", True, (130, 220, 160)), (box_rect.x + 25, y + 26))
                surface.blit(self.font_small.render(f"  Бонус: {bonus_txt}", True, (165, 185, 210)), (box_rect.x + 25, y + 44))

            xp_line = f"Опыт: {st.xp} / {st.xp_to_next}   |   HP: {int(st.hp)}/{st.max_hp}   |   MP: {int(st.mp)}/{st.max_mp}"
            surface.blit(self.font_main.render(xp_line, True, (240, 195, 75)), (box_rect.x + 25, box_rect.bottom - 44))

            hint = "W/S: Выбор характеристики  |  Enter: Вложить 1 очко  |  C / ESC: Закрыть"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return

        if self.mode == "skills":
            box_rect = pygame.Rect(290, 70, 700, 530)
            sk_mod = self.player.skills
            count = len(sk_mod.learned) if sk_mod else 0
            max_s = sk_mod.max_slots if sk_mod else 4
            self.draw_box(surface, box_rect, f"КНИГА НАВЫКОВ  |  Слоты памяти: {count} / {max_s}", True)

            if not sk_mod or not sk_mod.learned:
                surface.blit(self.font_main.render("Вы пока не изучили ни одного навыка.", True, (140, 145, 160)), (box_rect.x + 30, box_rect.y + 80))
                surface.blit(self.font_small.render("Купите книги у торговца и используйте их в рюкзаке [I].", True, (180, 190, 210)), (box_rect.x + 30, box_rect.y + 115))
            else:
                active_idx = 1
                for idx, sk in enumerate(sk_mod.learned):
                    y = box_rect.y + 65 + idx * 92
                    is_sel = (self.cursor == idx)
                    if is_sel:
                        pygame.draw.rect(surface, (45, 55, 75), (box_rect.x + 15, y - 6, box_rect.width - 30, 80), border_radius=4)
                    prefix = "▶ " if is_sel else "  "
                    color = (255, 255, 255) if is_sel else (200, 205, 220)

                    if sk.kind == "active":
                        tag = f"[АКТИВНЫЙ — КЛАВИША {active_idx}]  ({sk.mana_cost} MP, откат {sk.cooldown}с)"
                        tag_col = (100, 200, 255)
                        active_idx += 1
                    else:
                        tag = "[ПАССИВНЫЙ — ДЕЙСТВУЕТ ВСЕГДА]"
                        tag_col = (130, 225, 150)

                    surface.blit(self.font_title.render(f"{prefix}{sk.name}", True, color), (box_rect.x + 25, y))
                    surface.blit(self.font_small.render(f"   {tag}", True, tag_col), (box_rect.x + 25, y + 28))
                    surface.blit(self.font_small.render(f"   {sk.desc}", True, (185, 195, 210)), (box_rect.x + 25, y + 50))

            hint = "W/S: Выбор навыка  |  Enter: Забыть навык (освободить слот)  |  K / ESC: Закрыть"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return


        # 2. Отрисовка окон инвентаря, сундука или торговли
        left_rect = pygame.Rect(40, 35, 580, 460)
        right_rect = pygame.Rect(660, 35, 580, 460)
        info_rect = pygame.Rect(40, 515, 1200, 145)

        cap = f"{len(self.player.inventory.items)}/{self.player.inventory.capacity}"
        self.draw_box(surface, left_rect, f"РЮКЗАК ({cap})  |  Золото: {self.player.inventory.gold}G", self.active_side == "left")
        p_mode = "sell" if self.mode == "trade" else None
        self.draw_item_list(surface, left_rect, self.player.inventory.items, "left", p_mode)

        if self.mode == "inventory":
            self.draw_box(surface, right_rect, "ЭКИПИРОВКА И ХАРАКТЕРИСТИКИ", self.active_side == "right")
            for idx, (slot_key, item) in enumerate(self.player.equipment.slots.items()):
                y = right_rect.y + 56 + idx * 32
                is_sel = (self.active_side == "right" and self.cursor == idx)
                if is_sel:
                    pygame.draw.rect(surface, (45, 55, 75), (right_rect.x + 10, y - 4, right_rect.width - 20, 28), border_radius=3)
                prefix = "▶ " if is_sel else "  "
                color = (255, 255, 255) if is_sel else (200, 205, 220)
                item_name = item.name if item else "— пусто —"
                txt = self.font_main.render(f"{prefix}{SLOT_NAMES_RU[slot_key]}: {item_name}", True, color)
                surface.blit(txt, (right_rect.x + 16, y))

            st = self.player.stats
            cur_style = self.player.combat.get_weapon_style() if self.player.combat else "melee"
            pygame.draw.line(surface, (80, 90, 110), (right_rect.x + 16, right_rect.y + 286), (right_rect.right - 16, right_rect.y + 286), 2)
            lines = [
                f"Ур.{st.level} (XP:{st.xp}/{st.xp_to_next}) Очки:{st.stat_points}",
                f"HP: {int(st.hp)}/{st.max_hp} (+{st.hp_regen}/с)  MP: {int(st.mp)}/{st.max_mp} (+{st.mp_regen}/с)",
                f"Атака: {st.get_atk(cur_style)}  |  Защита: {st.get_def()}  |  Крит: {st.crit_chance}%",
                f"СИЛ:{st.str}  ЛОВ:{st.agi}  ИНТ:{st.int}  ЖИВ:{st.vit}  СТК:{st.end}"
            ]

            for i, line in enumerate(lines):
                surface.blit(self.font_main.render(line, True, (130, 220, 160)), (right_rect.x + 20, right_rect.y + 298 + i * 32))
            hint = "A/D: Сменить панель  |  W/S: Выбор  |  Enter: Надеть / Снять / Выпить  |  ESC / I: Закрыть"

        elif self.mode == "chest":
            self.draw_box(surface, right_rect, f"{self.target.name.upper()}", self.active_side == "right")
            self.draw_item_list(surface, right_rect, self.target.inventory.items, "right")
            hint = "A/D: Сменить панель  |  W/S: Выбор  |  Enter: Взять / Положить  |  ESC: Закрыть"

        elif self.mode == "trade":
            self.draw_box(surface, right_rect, f"ТОВАРЫ ТОРГОВЦА (Золото: {self.target.inventory.gold}G)", self.active_side == "right")
            self.draw_item_list(surface, right_rect, self.target.inventory.items, "right", "buy")
            hint = "A/D: Сменить панель  |  W/S: Выбор  |  Enter: Купить / Продать  |  ESC: Закрыть"

        sel_item = self.get_selected_item()
        self.draw_box(surface, info_rect, "ИНФОРМАЦИЯ О ПРЕДМЕТЕ", False)
        if sel_item:
            t_name = TYPE_NAMES_RU.get(sel_item.type, sel_item.type)
            header = f"{sel_item.name}   [{t_name}]   |   Цена: {sel_item.value}G (продажа: {max(1, sel_item.value // 2)}G)"
            stats_str = f"Свойства: {sel_item.get_stats_text()}"
            desc_str = f"Описание: {sel_item.description}"
            surface.blit(self.font_main.render(header, True, (245, 225, 130)), (info_rect.x + 20, info_rect.y + 52))
            surface.blit(self.font_main.render(stats_str, True, (120, 230, 150)), (info_rect.x + 20, info_rect.y + 80))
            surface.blit(self.font_small.render(desc_str, True, (185, 195, 210)), (info_rect.x + 20, info_rect.y + 108))
        else:
            surface.blit(self.font_main.render("Наведите курсор на предмет, чтобы увидеть его характеристики.", True, (130, 135, 150)), (info_rect.x + 20, info_rect.y + 65))

        pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
        surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))

