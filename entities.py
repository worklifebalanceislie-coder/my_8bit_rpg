import pygame
from components.inventory import Inventory
import random
from items import ITEMS_DB, SKILL_TO_ESSENCE
from factions import are_hostile
from components.effects import StatusEffects
from components.professions import ProfessionBook

class Entity:
    def __init__(self, name, x, y, color, sprite=None, is_container=False, faction="neutral", sprite_bank=None):
        self.name = name
        self.rect = pygame.Rect(x, y, 12, 12)
        self.color = color
        self.sprite = sprite
        self.sprite_key = None
        self.appearance = None
        self.sprite_bank = sprite_bank
        self.facing_left = False
        self.facing_dir = (1.0, 0.0)
        self.is_container = is_container
        self.is_loot_bag = False
        self.faction = faction
        self.hurt_timer = 0.0
        self.effects = StatusEffects(self)
        self.owner_lock = 0.0
        self.last_attacker = None
        self.speech_text = ""
        self.speech_timer = 0.0
        self.professions = ProfessionBook(self)
        self.quick_items = [None, None, None, None]  # 4 слота быстрого доступа (Q, F, Z, X)


        # Подключаемые модули
        self.movement = None
        self.inventory = None
        self.equipment = None
        self.stats = None
        self.combat = None
        self.skills = None
        self.ai = None
        self.quests = None
        self.dialogue = None
    
    def use_quick_item(self, slot_idx):
        if not self.inventory or slot_idx < 0 or slot_idx >= len(self.quick_items):
            return None
        item_id = self.quick_items[slot_idx]
        if not item_id:
            return None

        target_item = next((it for it in self.inventory.items if it.id == item_id), None)
        if not target_item:
            return "Предмет закончился в рюкзаке!"

        if target_item.type == "consumable":
            if "heal" in target_item.stats_bonus:
                heal = target_item.stats_bonus["heal"]
                self.stats.hp = min(float(self.stats.max_hp), self.stats.hp + heal)
                self.inventory.remove_item(target_item)
                return f"Использовано: {target_item.name} (+{heal} HP)"
            elif "mana" in target_item.stats_bonus:
                mana = target_item.stats_bonus["mana"]
                self.stats.mp = min(float(self.stats.max_mp), self.stats.mp + mana)
                self.inventory.remove_item(target_item)
                return f"Использовано: {target_item.name} (+{mana} MP)"
            elif "effect" in target_item.stats_bonus and self.effects:
                eff_id = target_item.stats_bonus["effect"]
                dur = 12.0 if eff_id == "shield" else 8.0
                self.effects.apply(eff_id, dur, power=1)
                self.inventory.remove_item(target_item)
                return f"Использовано: {target_item.name}"
            elif target_item.stats_bonus.get("cure") and self.effects:
                self.effects.remove("poison")
                self.effects.remove("burn")
                self.inventory.remove_item(target_item)
                return "Отрицательные эффекты сняты!"
            elif "expand_skill_slots" in target_item.stats_bonus and self.skills:
                new_lim = self.skills.expand_active_slots(target_item.stats_bonus["expand_skill_slots"])
                self.inventory.remove_item(target_item)
                return f"Слоты активных навыков расширены до {new_lim}!"
        return f"{target_item.name}: нельзя быстро применить"

    def say(self, text, duration=2.0):
        self.speech_text = text
        self.speech_timer = duration

    def interact(self, actor, ui):
        """Обрабатывает нажатие клавиши действия (E) рядом с этой сущностью"""
        # 1. Сундуки и мешки с лутом
        if self.is_container and self.inventory:
            gold_found = self.inventory.gold
            ui.open_container(self, "chest")
            if gold_found > 0:
                if actor.skills and actor.skills.has_skill("race_goblin"):
                    gold_found = int(gold_found * 1.5)
                return f"Найдено золота: +{gold_found}G!"
            return f"Открыто: {self.name}"

        # 2. Персонажи с диалогами, квестами или торговлей
        if self.ai:
            if are_hostile(self, actor):
                self.say("Прочь с дороги, враг!")
                return f"{self.name} враждебен к вам!"
            ui.open_dialogue(self)
            return f"Разговор: {self.name}"

        return None

    def respawn(self):
        """Возрождает сущность с полным запасом здоровья и маны на стартовой позиции"""
        if self.stats:
            self.stats.hp = float(self.stats.max_hp)
            self.stats.mp = float(self.stats.max_mp)
        if self.effects:
            self.effects.active.clear()
        start_pos = (420, 140) if self.faction in ("monster", "undead") else (180, 150)
        sx, sy = start_pos
        self.rect.topleft = start_pos
        if self.movement:
            self.movement.pos_x = float(sx)
            self.movement.pos_y = float(sy)

    def link_components(self):
        if self.stats:
            self.stats.equipment = self.equipment
            self.stats.skills = self.skills
            self.stats.effects = self.effects
        if self.inventory:
            self.inventory.equipment = self.equipment

    def take_damage(self, raw_damage, attacker, is_magic=False, effect=None, knockback_dir=None, walls=None):
        if not self.stats or self.stats.hp <= 0:
            return 0

        defense = self.stats.get_def()
        if is_magic:
            defense = defense // 2

        if attacker and attacker.stats:
            dmg, is_crit = attacker.stats.roll_damage(raw_damage, defense)
        else:
            dmg, is_crit = max(1, raw_damage - defense), False

        self.stats.hp = max(0.0, self.stats.hp - dmg)
        self.hurt_timer = 0.15
        self.last_attacker = attacker

        if effect and self.effects:
            eff_id, eff_dur, eff_pow = effect
            self.effects.apply(eff_id, eff_dur, eff_pow, source=attacker)
        elif is_crit:
            self.say("КРИТ!", 0.8)

        if knockback_dir and self.movement and walls is not None:
            kx, ky = knockback_dir
            self.movement.move(kx, ky, 0.04, walls)

        return dmg

    def update(self, dt, world):
        if self.owner_lock > 0:
            self.owner_lock -= dt
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        if self.effects:
            self.effects.update(dt)
        if self.speech_timer > 0:
            self.speech_timer -= dt
            if self.speech_timer <= 0:
                self.speech_text = ""

        if self.stats:
            self.stats.update(dt)
        if self.quests:
            self.quests.refresh_collect_quests()
        if self.skills:
            self.skills.update(dt)
        if self.combat:
            self.combat.update(dt)
        if self.ai:
            self.ai.update(dt, world)
        if self.movement:
            self.movement.update(dt)

    def drop_loot_bag(self, loot_sprite):
        bag = Entity(f"Лут ({self.name})", self.rect.x, self.rect.y, (180, 120, 60), sprite=loot_sprite, is_container=True)
        bag.is_loot_bag = True
        bag.owner_lock = 15.0
        bag.inventory = Inventory(capacity=30, gold=0)

        if self.inventory:
            bag.inventory.gold += self.inventory.gold
            for item in list(self.inventory.items):
                bag.inventory.add_item(item)

        if self.equipment:
            for slot, item in self.equipment.slots.items():
                if item:
                    bag.inventory.add_item(item)

        # Шанс 45% выбить эссенцию одного из изученных навыков погибшего
        if self.skills and self.skills.learned:
            if random.random() < 0.45:
                chosen_skill = random.choice(self.skills.learned)
                essence_key = SKILL_TO_ESSENCE.get(chosen_skill.id)
                if essence_key and essence_key in ITEMS_DB:
                    bag.inventory.add_item(ITEMS_DB[essence_key])

        return bag

    def build_animated_sprite(self):
        if self.appearance and self.sprite is None:
            from appearance import build_character_sprite
            self.sprite = build_character_sprite(self.appearance)

        composite = pygame.Surface((20, 18), pygame.SRCALPHA)
        body = self.sprite.copy()


        if self.equipment and self.sprite_bank:
            armor = self.equipment.slots.get("armor")
            if armor:
                a_key = armor.sprite_key or f"equip_{armor.id}"
                armor_spr = self.sprite_bank.get(a_key)
                if armor_spr:
                    body.blit(armor_spr, (0, 0))

        bob_y = 0
        if self.movement and self.movement.walk_timer > 0:
            step_phase = int(self.movement.walk_timer) % 4
            if step_phase in (1, 3):
                bob_y = -1

            upper = body.subsurface((0, 0, 16, 12))
            left_leg = body.subsurface((0, 12, 8, 4))
            right_leg = body.subsurface((8, 12, 8, 4))

            composite.blit(upper, (0, 2 + bob_y))
            if step_phase == 1:
                composite.blit(left_leg, (1, 13))
                composite.blit(right_leg, (7, 14))
            elif step_phase == 3:
                composite.blit(left_leg, (0, 14))
                composite.blit(right_leg, (8, 13))
            else:
                composite.blit(left_leg, (0, 14))
                composite.blit(right_leg, (8, 14))
        else:
            composite.blit(body, (0, 2))

        if self.equipment and self.sprite_bank:
            weapon = self.equipment.slots.get("weapon")
            if weapon:
                w_key = weapon.sprite_key or f"equip_{weapon.id}"
                weapon_spr = self.sprite_bank.get(w_key)
                if weapon_spr:
                    is_swinging = self.combat and self.combat.swing_timer > 0
                    if is_swinging:
                        if weapon.combat_style == "melee":
                            swung_weapon = pygame.transform.rotate(weapon_spr, -55)
                            composite.blit(swung_weapon, (4, 3))
                        else:
                            composite.blit(weapon_spr, (3, 2 + bob_y))
                    else:
                        composite.blit(weapon_spr, (0, 2 + bob_y))

        return composite

    def draw(self, surface, font=None):
        if self.sprite:
            img = self.build_animated_sprite()
            lunge_x = 0
            if self.combat and self.combat.swing_timer > 0:
                lunge_x = -3 if self.facing_left else 3

            if self.facing_left:
                img = pygame.transform.flip(img, True, False)
                surface.blit(img, (self.rect.x - 6 + lunge_x, self.rect.y - 6))
            else:
                surface.blit(img, (self.rect.x - 2 + lunge_x, self.rect.y - 6))

            if self.hurt_timer > 0:
                pygame.draw.rect(surface, (230, 60, 60), self.rect, 1)
            elif self.effects: self.effects.draw(surface)
        else:
            pygame.draw.rect(surface, self.color, self.rect)

        if self.combat:
            self.combat.draw(surface)

        if self.stats and self.stats.hp < self.stats.max_hp:
            bar_w = 14
            hp_ratio = max(0.0, self.stats.hp / self.stats.max_hp)
            pygame.draw.rect(surface, (20, 20, 20), (self.rect.x - 1, self.rect.y - 8, bar_w, 3))
            pygame.draw.rect(surface, (220, 50, 50), (self.rect.x - 1, self.rect.y - 8, int(bar_w * hp_ratio), 3))

    def draw_speech(self, screen, camera, scale, font):
        if not font or not self.speech_text or self.speech_timer <= 0:
            return
        txt_surf = font.render(self.speech_text, True, (255, 250, 210))
        scr_cx = (self.rect.centerx - camera.offset_x) * scale
        scr_top = (self.rect.y - camera.offset_y) * scale
        tx = int(scr_cx - txt_surf.get_width() // 2)
        ty = int(scr_top - 22 - txt_surf.get_height())

        bg_rect = pygame.Rect(tx - 6, ty - 3, txt_surf.get_width() + 12, txt_surf.get_height() + 6)
        pygame.draw.rect(screen, (18, 22, 30), bg_rect, border_radius=4)
        pygame.draw.rect(screen, (90, 105, 130), bg_rect, 1, border_radius=4)
        screen.blit(txt_surf, (tx, ty))
