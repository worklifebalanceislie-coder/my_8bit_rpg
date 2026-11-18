import pygame
from components.inventory import Inventory
import random
from items import ITEMS_DB, SKILL_TO_ESSENCE
from factions import are_hostile
from components.effects import StatusEffects

class Entity:
    def __init__(self, name, x, y, color, sprite=None, is_container=False, faction="neutral", sprite_bank=None):
        self.name = name
        self.rect = pygame.Rect(x, y, 12, 12)
        self.color = color
        self.sprite = sprite
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

        # Подключаемые модули
        self.movement = None
        self.inventory = None
        self.equipment = None
        self.stats = None
        self.combat = None
        self.skills = None
        self.ai = None
        self.skills = None
        self.quests = None
        self.dialogue = None
        self.ai = None


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

        if self.speech_text and font:
            txt = font.render(self.speech_text, False, (255, 240, 150))
            surface.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.y - 16))
