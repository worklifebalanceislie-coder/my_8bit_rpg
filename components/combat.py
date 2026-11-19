import pygame
import math
from factions import are_hostile
import random

class Projectile:
    def __init__(self, x, y, dx, dy, owner, damage, kind="arrow"):
        self.owner = owner
        self.damage = damage
        self.kind = kind
        self.speed = 190 if kind == "arrow" else 135
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.dx = dx
        self.dy = dy
        self.life = 1.6
        self.alive = True
        size = 4 if kind == "arrow" else 6
        self.rect = pygame.Rect(int(x) - size // 2, int(y) - size // 2, size, size)

    def update(self, dt, world):
        if not self.alive:
            return

        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return

        self.pos_x += self.dx * self.speed * dt
        self.pos_y += self.dy * self.speed * dt
        self.rect.center = (round(self.pos_x), round(self.pos_y))

        for wall in world.walls:
            if self.rect.colliderect(wall):
                self.alive = False
                return

        for target in world.entities:
            if target is self.owner or not target.stats or target.stats.hp <= 0:
                continue
            # Снаряд не ранит союзников, если между ними нет вражды
            if target.faction == self.owner.faction and not are_hostile(self.owner, target):
                continue

            if self.rect.colliderect(target.rect):
                is_magic = self.kind in ("fireball", "ice")
                eff = None
                if self.kind == "ice":
                    eff = ("slow", 3.5, 1)
                elif self.kind == "fireball" and (pygame.time.get_ticks() % 2 == 0):
                    eff = ("burn", 3.0, 2)

                target.take_damage(
                    self.damage,
                    attacker=self.owner,
                    is_magic=is_magic,
                    effect=eff,
                    knockback_dir=(self.dx, self.dy),
                    walls=world.walls
                )
                self.alive = False
                return


    def draw(self, surface):
        if not self.alive:
            return
        if self.kind == "arrow":
            end_x = int(self.pos_x + self.dx * 6)
            end_y = int(self.pos_y + self.dy * 6)
            start_x = int(self.pos_x - self.dx * 4)
            start_y = int(self.pos_y - self.dy * 4)
            pygame.draw.line(surface, (180, 125, 65), (start_x, start_y), (end_x, end_y), 1)
            pygame.draw.circle(surface, (220, 230, 240), (end_x, end_y), 1)
        elif self.kind == "fireball":
            cx, cy = int(self.pos_x), int(self.pos_y)
            pygame.draw.circle(surface, (235, 85, 30), (cx, cy), 4)
            pygame.draw.circle(surface, (255, 225, 90), (cx, cy), 2)
        elif self.kind == "ice":
            cx, cy = int(self.pos_x), int(self.pos_y)
            pygame.draw.circle(surface, (80, 190, 255), (cx, cy), 4)
            pygame.draw.circle(surface, (210, 245, 255), (cx, cy), 2)


class Combat:
    def __init__(self, owner, cooldown=0.5, attack_range=16):
        self.owner = owner
        self.cooldown = cooldown
        self.timer = 0.0
        self.attack_range = attack_range
        self.swing_timer = 0.0
        self.swing_rect = None

    def get_weapon_style(self):
        if self.owner.equipment:
            weapon = self.owner.equipment.slots.get("weapon")
            if weapon:
                return weapon.combat_style
        return "melee"

    def update(self, dt):
        if self.timer > 0:
            self.timer -= dt
        if self.swing_timer > 0:
            self.swing_timer -= dt
            if self.swing_timer <= 0:
                self.swing_rect = None

    def attack(self, world, aim_pos=None):
        if self.timer > 0 or not self.owner.stats or self.owner.stats.hp <= 0:
            return False

        style = self.get_weapon_style()
        cx, cy = self.owner.rect.center

        if aim_pos is not None:
            ax, ay = aim_pos
            vx, vy = ax - cx, ay - cy
            dist = math.hypot(vx, vy)
            if dist > 0.001:
                dx, dy = vx / dist, vy / dist
            else:
                dx, dy = (-1.0 if self.owner.facing_left else 1.0), 0.0
            self.owner.facing_left = (dx < 0)
        else:
            dx = -1.0 if self.owner.facing_left else 1.0
            dy = 0.0

        # --- ДАЛЬНИЙ БОЙ (ЛУК ИЛИ ПОСОХ) ---
        if style in ("bow", "staff"):
            if style == "staff":
                if self.owner.stats.mp < 10:
                    return False
                self.owner.stats.mp -= 10

            self.timer = self.cooldown
            self.swing_timer = 0.18
            base_dmg = self.owner.stats.get_atk(style)
            is_crit = random.randint(1, 100) <= self.owner.stats.crit_chance
            dmg = int(base_dmg * 1.6) if is_crit else base_dmg

            p_kind = "fireball" if style == "staff" else "arrow"
            proj = Projectile(cx + dx * 8, cy + dy * 8, dx, dy, self.owner, dmg, p_kind)
            world.projectiles.append(proj)
            return True

        # --- БЛИЖНИЙ БОЙ (МЕЧ / РУКОПАШНАЯ НА 360°) ---
        self.timer = self.cooldown
        self.swing_timer = 0.18

        hit_cx = int(cx + dx * 13)
        hit_cy = int(cy + dy * 13)
        self.swing_rect = pygame.Rect(0, 0, 24, 24)
        self.swing_rect.center = (hit_cx, hit_cy)

        base_dmg = self.owner.stats.get_atk("melee")
        for ent in list(world.entities):
            if ent is self.owner or not ent.stats or ent.stats.hp <= 0:
                continue
            if ent.faction == self.owner.faction and not are_hostile(self.owner, ent):
                continue
            if self.swing_rect.colliderect(ent.rect):
                is_crit = random.randint(1, 100) <= self.owner.stats.crit_chance
                raw_dmg = int(base_dmg * 1.6) if is_crit else base_dmg
                ent.take_damage(
                    raw_dmg,
                    attacker=self.owner,
                    is_magic=False,
                    knockback_dir=(dx, dy),
                    walls=world.walls
                )
                if is_crit:
                    ent.say("КРИТ!", 0.8)

        return True

    def draw(self, surface):
        if self.get_weapon_style() == "melee" and self.swing_rect and self.swing_timer > 0:
            r = self.swing_rect
            if self.owner.facing_left:
                pygame.draw.line(surface, (230, 245, 255), (r.right - 4, r.top + 3), (r.left + 2, r.centery), 2)
                pygame.draw.line(surface, (150, 200, 255), (r.left + 2, r.centery), (r.right - 4, r.bottom - 3), 2)
            else:
                pygame.draw.line(surface, (230, 245, 255), (r.left + 4, r.top + 3), (r.right - 2, r.centery), 2)
                pygame.draw.line(surface, (150, 200, 255), (r.right - 2, r.centery), (r.left + 4, r.bottom - 3), 2)
