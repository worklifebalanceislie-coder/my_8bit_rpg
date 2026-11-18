import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT
from components.trade import Trade
from components.inventory import Inventory
from components.quests import Quest
from entities import Entity
from items import ITEMS_DB
from components.professions import PROFESSIONS_DB, RECIPES_DB

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
    "book": "Книга навыка",
    "misc": "Ценность"
}

class UIManager:
    def __init__(self, player, entities=None, loot_sprite=None):
        self.player = player
        self.entities = entities
        self.loot_sprite = loot_sprite
        self.is_open = False
        self.mode = None
        self.target = None
        self.active_side = "left"
        self.cursor = 0
        self.dialogue_reply = ""
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

    def open_quests(self):
        self.is_open = True
        self.mode = "quests"
        self.target = None
        self.active_side = "left"
        self.cursor = 0

    def open_professions(self):
        self.is_open = True
        self.mode = "professions"
        self.target = None
        self.active_side = "left"
        self.cursor = 0

    def get_available_recipes(self):
        if not getattr(self.player, "professions", None):
            return []
        return [r for r in RECIPES_DB.values() if self.player.professions.has_profession(r.prof_id)]

    def open_dialogue(self, npc):
        self.is_open = True
        self.mode = "dialogue"
        self.target = npc
        self.active_side = "left"
        self.cursor = 0
        self.dialogue_reply = npc.dialogue.get("greeting", "Приветствую, путник!") if npc.dialogue else "Приветствую!"

    def open_container(self, target, mode):
        self.is_open = True
        self.mode = mode
        self.target = target
        self.active_side = "right"
        self.cursor = 0
        if mode == "chest" and target.inventory and target.inventory.gold > 0:
            gold = target.inventory.gold
            if self.player.skills and self.player.skills.has_skill("race_goblin"):
                gold = int(gold * 1.5)
            self.player.inventory.gold += gold
            target.inventory.gold = 0

    def close(self):
        self.is_open = False
        self.mode = None
        self.target = None

    def get_dialogue_options(self):
        npc = self.target
        if not npc:
            return []
        opts = []
        dlg = npc.dialogue or {}

        # Квест НПС
        q_data = dlg.get("quest")
        if q_data and self.player.quests:
            existing = self.player.quests.get_quest(q_data["id"])
            if not existing:
                opts.append(("accept_quest", f"[Задание] {q_data['title']}"))
            elif existing.status == "active":
                opts.append(("check_quest", f"[В процессе] {existing.title}"))
            elif existing.status == "ready":
                opts.append(("turn_in_quest", f"[Сдать задание!] {existing.title}"))

        # Обучение профессии у НПС
        teach = dlg.get("teach_profession")
        if teach and getattr(self.player, "professions", None):
            p_id = teach["id"]
            if p_id in PROFESSIONS_DB and not self.player.professions.has_profession(p_id):
                p_name = PROFESSIONS_DB[p_id].name
                cost = teach.get("cost", 0)
                cost_str = f" ({cost}G)" if cost > 0 else " (Бесплатно)"
                opts.append(("learn_prof", f"[Обучение] Профессия: {p_name}{cost_str}"))

        # Торговля
        if npc.ai and npc.ai.role == "merchant" and npc.inventory:
            opts.append(("open_trade", "Посмотреть товары (Торговля)"))

        opts.append(("rumor", "Спросить о новостях"))
        opts.append(("bye", "До свидания"))
        return opts

    def get_current_list_len(self):
        if self.mode == "stats":
            return 5
        if self.mode == "skills":
            return len(self.player.skills.learned) if self.player.skills else 0
        if self.mode == "quests":
            return len(self.player.quests.quests) if self.player.quests else 0
        if self.mode == "dialogue":
            return len(self.get_dialogue_options())
        if self.mode == "professions":
            return len(self.get_available_recipes())
        if self.active_side == "left":
            return len(self.player.inventory.items)
        if self.mode == "inventory":
            return len(self.player.equipment.slots)
        if self.target and self.target.inventory:
            return len(self.target.inventory.items)
        return 0
    
    def get_selected_item(self):
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

    def handle_global_hotkey(self, event):
        if self.is_open or event.type != pygame.KEYDOWN:
            return False
        if event.key in (pygame.K_i, pygame.K_TAB):
            self.open_inventory()
            return True
        if event.key == pygame.K_c:
            self.open_stats()
            return True
        if event.key == pygame.K_k:
            self.open_skills()
            return True
        if event.key == pygame.K_j:
            self.open_quests()
            return True
        if event.key == pygame.K_p:
            self.open_professions()
            return True
        return False

    def handle_input(self, event):
        if not self.is_open or event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_ESCAPE, pygame.K_i, pygame.K_TAB, pygame.K_c, pygame.K_k, pygame.K_j, pygame.K_p):
            self.close()
            return "Окно закрыто"

        if self.mode in ("inventory", "chest", "trade"):
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

        if event.key in (pygame.K_x, pygame.K_DELETE):
            return self.drop_selected_item()

        return None

    def drop_selected_item(self):
        if self.mode != "inventory" or self.active_side != "left":
            return None
        items = self.player.inventory.items
        if not items or self.cursor >= len(items):
            return None

        item = items[self.cursor]
        if not self.player.inventory.remove_item(item):
            return None

        self.cursor = max(0, min(self.cursor, len(items) - 1))

        if self.entities is not None:
            bag = None
            for ent in self.entities:
                if getattr(ent, "is_loot_bag", False) and self.player.rect.inflate(16, 16).colliderect(ent.rect):
                    bag = ent
                    break

            if bag is None:
                bag = Entity("Сброшенный лут", self.player.rect.x, self.player.rect.y, (180, 120, 60), sprite=self.loot_sprite, is_container=True)
                bag.is_loot_bag = True
                bag.inventory = Inventory(capacity=30, gold=0)
                self.entities.append(bag)

            bag.inventory.add_item(item)

        return f"Выброшено: {item.name}"

    def perform_action(self):
        if self.mode == "inventory":
            if self.active_side == "left":
                items = self.player.inventory.items
                if not items or self.cursor >= len(items):
                    return None
                item = items[self.cursor]
                if item.type in self.player.equipment.slots:
                    if self.player.equipment.equip(item, self.player.inventory):
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                        return f"Надето: {item.name}"
                    return "Нельзя надеть (нет места в сумке)"
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
                    elif "effect" in item.stats_bonus and self.player.effects:
                        eff_id = item.stats_bonus["effect"]
                        dur = 12.0 if eff_id == "shield" else 8.0
                        self.player.effects.apply(eff_id, dur, power=1)
                        self.player.inventory.remove_item(item)
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                        return f"Выпито: {item.name}"
                    elif item.stats_bonus.get("cure") and self.player.effects:
                        self.player.effects.remove("poison")
                        self.player.effects.remove("burn")
                        self.player.inventory.remove_item(item)
                        self.cursor = max(0, min(self.cursor, len(items) - 1))
                        return "Отрицательные эффекты сняты!"
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
                    return "Рюкзак полон или перегружен!"

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

        elif self.mode == "trade" and self.target:
            if self.active_side == "right":
                items = self.target.inventory.items
                if items and self.cursor < len(items):
                    item = items[self.cursor]
                    ok, msg = Trade.buy_item(self.player.inventory, self.target.inventory, item, self.player)
                    self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return msg
            elif self.active_side == "left":
                items = self.player.inventory.items
                if items and self.cursor < len(items):
                    item = items[self.cursor]
                    ok, msg = Trade.sell_item(self.player.inventory, self.target.inventory, item, self.player)
                    self.cursor = max(0, min(self.cursor, len(items) - 1))
                    return msg

        elif self.mode == "stats":
            stat_keys = ["str", "agi", "int", "vit", "end"]
            stat_names = ["Сила", "Ловкость", "Интеллект", "Живучесть", "Стойкость"]
            chosen = stat_keys[self.cursor]
            if self.player.stats.upgrade_stat(chosen):
                return f"Улучшено: {stat_names[self.cursor]} (+1)"
            return "Нет свободных очков характеристик!"

        elif self.mode == "skills" and self.player.skills:
            ok, msg = self.player.skills.forget_skill(self.cursor)
            if ok:
                self.cursor = max(0, min(self.cursor, len(self.player.skills.learned) - 1))
                return msg

        elif self.mode == "professions" and getattr(self.player, "professions", None):
            recs = self.get_available_recipes()
            if recs and self.cursor < len(recs):
                _, msg = self.player.professions.craft(recs[self.cursor])
                return msg

        elif self.mode == "dialogue" and self.target:
            opts = self.get_dialogue_options()
            if not opts or self.cursor >= len(opts):
                return None
            act_id, _ = opts[self.cursor]
            dlg = self.target.dialogue or {}

            if act_id == "accept_quest":
                qd = dlg["quest"]
                new_q = Quest(
                    qd["id"], qd["title"], qd["desc"], self.target.name,
                    qd["target_type"], qd["target_id"], qd["count"],
                    qd.get("gold", 0), qd.get("xp", 0), qd.get("item")
                )
                ok, msg = self.player.quests.add_quest(new_q)
                self.dialogue_reply = qd.get("accept_text", "Отлично! Буду ждать тебя с новостями.")
                self.cursor = 0
                return msg
            
            elif act_id == "learn_prof":
                teach = dlg.get("teach_profession")
                p_id = teach["id"]
                cost = teach.get("cost", 0)
                if self.player.inventory.gold < cost:
                    self.dialogue_reply = f"Обучение стоит {cost} золота. Возвращайся, когда накопишь!"
                    return f"Недостаточно золота (нужно {cost}G)"
                ok, msg = self.player.professions.learn(p_id, level=1)
                if ok:
                    self.player.inventory.gold -= cost
                    self.dialogue_reply = teach.get("text", "Отлично! Теперь ты знаешь основы этого ремесла. Нажми [P], чтобы открыть верстак.")
                    self.cursor = 0
                return msg

            elif act_id == "check_quest":
                self.dialogue_reply = dlg.get("progress_text", "Ты еще не выполнил мою просьбу.")
                return None

            elif act_id == "turn_in_quest":
                qd = dlg["quest"]
                ok, msg = self.player.quests.complete_quest(qd["id"])
                if ok:
                    self.dialogue_reply = qd.get("complete_text", "Отличная работа! Вот твоя награда.")
                    self.cursor = 0
                return msg

            elif act_id == "open_trade":
                self.open_container(self.target, "trade")
                return f"Торговля: {self.target.name}"

            elif act_id == "rumor":
                self.dialogue_reply = dlg.get("rumor", "Говорят, у озера на востоке расплодились монстры.")
                return None

            elif act_id == "bye":
                self.close()
                return "Разговор окончен"

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
                price = Trade.get_buy_price(self.player, item)
                label = f"{prefix}{item.name}  [{price}G]"
            elif price_mode == "sell":
                price = Trade.get_sell_price(self.player, item)
                label = f"{prefix}{item.name}  [{price}G]"
            txt = self.font_main.render(str(label), True, color)
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
            hint = "W/S: Выбор навыка  |  Enter: Забыть навык  |  K / ESC: Закрыть"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return

        if self.mode == "quests":
            box_rect = pygame.Rect(260, 70, 760, 540)
            q_list = self.player.quests.quests if self.player.quests else []
            self.draw_box(surface, box_rect, f"ЖУРНАЛ ЗАДАНИЙ  |  Всего: {len(q_list)}", True)
            if not q_list:
                surface.blit(self.font_main.render("У вас пока нет активных заданий.", True, (140, 145, 160)), (box_rect.x + 30, box_rect.y + 80))
                surface.blit(self.font_small.render("Поговорите со стражником или торговцем на площади [E].", True, (180, 190, 210)), (box_rect.x + 30, box_rect.y + 115))
            else:
                for idx, q in enumerate(q_list):
                    y = box_rect.y + 62 + idx * 105
                    is_sel = (self.cursor == idx)
                    if is_sel:
                        pygame.draw.rect(surface, (45, 55, 75), (box_rect.x + 15, y - 6, box_rect.width - 30, 92), border_radius=4)
                    status_map = {
                        "active": (f"В процессе ({q.current_count}/{q.required_count})", (240, 200, 80)),
                        "ready": ("ГОТОВО К СДАЧЕ!", (100, 235, 130)),
                        "completed": ("ЗАВЕРШЕНО", (130, 135, 150))
                    }
                    st_txt, st_col = status_map.get(q.status, ("", (255, 255, 255)))
                    prefix = "▶ " if is_sel else "  "
                    surface.blit(self.font_title.render(f"{prefix}{q.title}  [{st_txt}]", True, st_col), (box_rect.x + 25, y))
                    surface.blit(self.font_small.render(f"   Заказчик: {q.giver_name}  |  {q.desc}", True, (210, 215, 230)), (box_rect.x + 25, y + 28))
                    rew = f"Награда: {q.reward_gold}G, {q.reward_xp} XP" + (f" + {ITEMS_DB[q.reward_item].name}" if q.reward_item else "")
                    surface.blit(self.font_small.render(f"   {rew}", True, (140, 210, 255)), (box_rect.x + 25, y + 52))
            hint = "W/S: Выбор задания  |  J / ESC: Закрыть"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return

        if self.mode == "professions":
            box_rect = pygame.Rect(220, 60, 840, 560)
            p_book = getattr(self.player, "professions", None)
            learned_str = ", ".join(
                f"{PROFESSIONS_DB[pid].name} (Ур.{info['level']} | {info['xp']}/{info['xp_next']} XP)"
                for pid, info in p_book.learned.items() if pid in PROFESSIONS_DB
            ) if (p_book and p_book.learned) else "Нет изученных профессий"

            self.draw_box(surface, box_rect, "ПРОФЕССИИ И РЕМЕСЛО", True)
            surface.blit(self.font_small.render(f"Ваши навыки: {learned_str}", True, (130, 235, 160)), (box_rect.x + 25, box_rect.y + 52))
            pygame.draw.line(surface, (80, 90, 110), (box_rect.x + 20, box_rect.y + 80), (box_rect.right - 20, box_rect.y + 80), 1)

            recs = self.get_available_recipes()
            if not recs:
                surface.blit(self.font_main.render("Нет доступных рецептов для ваших профессий.", True, (150, 155, 170)), (box_rect.x + 30, box_rect.y + 110))
            else:
                for idx, rec in enumerate(recs[:6]):
                    y = box_rect.y + 92 + idx * 72
                    is_sel = (self.cursor == idx)
                    if is_sel:
                        pygame.draw.rect(surface, (45, 55, 75), (box_rect.x + 15, y - 4, box_rect.width - 30, 62), border_radius=4)

                    res_item = ITEMS_DB.get(rec.result_item_id)
                    res_name = res_item.name if res_item else rec.result_item_id
                    prof_name = PROFESSIONS_DB[rec.prof_id].name if rec.prof_id in PROFESSIONS_DB else rec.prof_id
                    can_make, reason = p_book.can_craft(rec)

                    col = (255, 255, 255) if is_sel else (200, 205, 220)
                    prefix = "▶ " if is_sel else "  "
                    surface.blit(self.font_title.render(f"{prefix}{res_name}  [{prof_name} Ур.{rec.req_level}]", True, col), (box_rect.x + 25, y))

                    mats_parts = []
                    for m_id, req_q in rec.materials.items():
                        m_name = ITEMS_DB[m_id].name if m_id in ITEMS_DB else m_id
                        have_q = sum(1 for it in self.player.inventory.items if it.id == m_id)
                        mats_parts.append(f"{m_name}: {have_q}/{req_q}")
                    mats_line = "Материалы: " + ", ".join(mats_parts)
                    st_col = (120, 230, 150) if can_make else (240, 130, 110)
                    surface.blit(self.font_small.render(f"   {mats_line}   |   {reason}", True, st_col), (box_rect.x + 25, y + 30))

            hint = "W/S: Выбор рецепта  |  Enter: Создать предмет  |  P / ESC: Закрыть"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return

        if self.mode == "dialogue" and self.target:
            box_rect = pygame.Rect(240, 110, 800, 480)
            self.draw_box(surface, box_rect, f"ДИАЛОГ: {self.target.name.upper()}", True)
            pygame.draw.rect(surface, (28, 34, 48), (box_rect.x + 20, box_rect.y + 56, box_rect.width - 40, 110), border_radius=6)
            surface.blit(self.font_main.render(f"«{self.dialogue_reply}»", True, (245, 235, 190)), (box_rect.x + 35, box_rect.y + 95))
            opts = self.get_dialogue_options()
            for idx, (_, label) in enumerate(opts):
                y = box_rect.y + 190 + idx * 46
                is_sel = (self.cursor == idx)
                if is_sel:
                    pygame.draw.rect(surface, (45, 58, 82), (box_rect.x + 20, y - 6, box_rect.width - 40, 38), border_radius=4)
                prefix = "▶ " if is_sel else "  "
                col = (255, 255, 255) if is_sel else (190, 200, 215)
                surface.blit(self.font_main.render(f"{prefix}{label}", True, col), (box_rect.x + 30, y))
            hint = "W/S: Выбор реплики  |  Enter: Ответить  |  ESC: Уйти"
            pygame.draw.rect(surface, (15, 18, 26), (0, WINDOW_HEIGHT - 36, WINDOW_WIDTH, 36))
            surface.blit(self.font_small.render(hint, True, (230, 230, 230)), (40, WINDOW_HEIGHT - 27))
            return

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
            hint = "A/D: Панель | W/S: Выбор | Enter: Надеть/Исп. | X: Выбросить | ESC: Выход"

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
