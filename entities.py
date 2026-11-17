import pygame
from components.inventory import Inventory

class Entity:
    def __init__(self, name, x, y, color, sprite=None, is_container=False, faction="neutral", sprite_bank=None):
        self.name = name
        self.rect = pygame.Rect(x, y, 12, 12)
        self.color = color
        self.sprite = sprite
        self.sprite_bank = sprite_bank
        self.facing_left = False
        self.is_container = is_container
        self.faction = faction
        self.hurt_timer = 0.0
        self.last_attacker = None
        self.speech_text = ""
        self.speech_timer = 0.0
        self.skills = None
        self.slow_timer = 0.0
        self.movement = None
        self.inventory = None
        self.equipment = None
        self.stats = None
        self.combat = None
        self.ai = None

    def say(self, text, duration=2.0):
        self.speech_text = text
        self.speech_timer = duration

    def link_components(self):
        if self.stats and self.equipment:
            self.stats.equipment = self.equipment
        if self.inventory and self.equipment:
            self.inventory.equipment = self.equipment
        if self.stats and self.skills:
            self.stats.skills = self.skills


    def update(self, dt, walls, entities=None, projectiles=None):
        if self.stats:
            self.stats.update(dt)
        if getattr(self, "owner_lock", 0) > 0:
            self.owner_lock -= dt
        if self.hurt_timer > 0:
            self.hurt_timer -= dt
        if self.speech_timer > 0:
            self.speech_timer -= dt
            if self.speech_timer <= 0:
                self.speech_text = ""
        if self.combat:
            self.combat.update(dt)
        if self.ai:
            self.ai.update(dt, walls, entities, projectiles)
        if self.movement:
            self.movement.update(dt)
        if self.slow_timer > 0:
            self.slow_timer -= dt
        if self.skills:
            self.skills.update(dt)


    def drop_loot_bag(self, loot_sprite):
        bag = Entity(f"Лут ({self.name})", self.rect.x, self.rect.y, (180, 120, 60), sprite=loot_sprite, is_container=True)
        bag.inventory = Inventory(capacity=30, gold=0)
        bag.owner_lock = 15.0  # 15 секунд ИИ не трогает этот мешок, чтобы игрок успел забрать лут

        if self.inventory:
            bag.inventory.gold += self.inventory.gold
            for item in list(self.inventory.items):
                bag.inventory.add_item(item)

        if self.equipment:
            for slot, item in self.equipment.slots.items():
                if item:
                    bag.inventory.add_item(item)
        return bag


    def build_animated_sprite(self):
        composite = pygame.Surface((20, 18), pygame.SRCALPHA)
        body = self.sprite.copy()

        if self.equipment and self.sprite_bank:
            armor = self.equipment.slots.get("armor")
            if armor:
                armor_spr = self.sprite_bank.get(f"equip_{armor.id}")
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
                weapon_spr = self.sprite_bank.get(f"equip_{weapon.id}")
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
        else:
            pygame.draw.rect(surface, self.color, self.rect)

        if self.combat:
            self.combat.draw(surface)

        if self.slow_timer > 0:
            pygame.draw.rect(surface, (100, 210, 255), self.rect, 1)

        if self.stats and self.stats.hp < self.stats.max_hp:
            bar_w = 14
            hp_ratio = max(0.0, self.stats.hp / self.stats.max_hp)
            pygame.draw.rect(surface, (20, 20, 20), (self.rect.x - 1, self.rect.y - 8, bar_w, 3))
            pygame.draw.rect(surface, (220, 50, 50), (self.rect.x - 1, self.rect.y - 8, int(bar_w * hp_ratio), 3))

        if self.speech_text and font:
            txt = font.render(self.speech_text, False, (255, 240, 150))
            surface.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.y - 16))
