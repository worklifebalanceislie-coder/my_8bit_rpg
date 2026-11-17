import pygame
import math

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

    def update(self, dt, walls, entities):
        if not self.alive:
            return

        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return

        self.pos_x += self.dx * self.speed * dt
        self.pos_y += self.dy * self.speed * dt
        self.rect.center = (round(self.pos_x), round(self.pos_y))

        for wall in walls:
            if self.rect.colliderect(wall):
                self.alive = False
                return

        for target in entities:
            if target is self.owner or not target.stats or target.stats.hp <= 0:
                continue
            if target.faction == self.owner.faction:
                continue

            if self.rect.colliderect(target.rect):
                defense = target.stats.get_def()
                if self.kind in ("fireball", "ice"):
                    defense = defense // 2
                dmg, is_crit = self.owner.stats.roll_damage(self.damage, defense)
                target.stats.hp = max(0.0, target.stats.hp - dmg)
                target.hurt_timer = 0.15
                target.last_attacker = self.owner
                if self.kind == "ice":
                    target.slow_timer = 3.0
                    target.say("Замедлен!", 0.9)
                elif is_crit:
                    target.say("КРИТ!", 0.8)

                if target.movement:
                    target.movement.move(self.dx, self.dy, 0.04, walls)

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

    def attack(self, targets, projectiles=None, aim_pos=None, walls=None):
        if self.timer > 0 or not self.owner.stats:
            return False

        if walls is None:
            walls = []

        style = self.get_weapon_style()
        atk_power = self.owner.stats.get_atk(style)

        if style in ("bow", "staff") and projectiles is not None:
            if style == "staff":
                mana_cost = 10
                if self.owner.stats.mp < mana_cost:
                    self.owner.say("Мало маны!", 0.8)
                    return False
                self.owner.stats.mp -= mana_cost

            self.timer = self.cooldown + (0.15 if style == "staff" else 0.05)
            self.swing_timer = 0.12

            if aim_pos:
                ax, ay = aim_pos
                dx = ax - self.owner.rect.centerx
                dy = ay - self.owner.rect.centery
                dist = math.hypot(dx, dy)
                if dist > 0:
                    dx, dy = dx / dist, dy / dist
                else:
                    dx, dy = getattr(self.owner, "facing_dir", (1.0, 0.0))
                if dx != 0:
                    self.owner.facing_left = (dx < 0)
            else:
                dx, dy = getattr(self.owner, "facing_dir", (-1.0 if self.owner.facing_left else 1.0, 0.0))


            kind = "arrow" if style == "bow" else "fireball"
            proj = Projectile(self.owner.rect.centerx + dx * 6, self.owner.rect.centery, dx, dy, self.owner, atk_power, kind)
            projectiles.append(proj)
            return True

        self.timer = self.cooldown
        self.swing_timer = 0.16

        reach = self.attack_range + 4
        hit_x = self.owner.rect.centerx - reach if self.owner.facing_left else self.owner.rect.centerx
        self.swing_rect = pygame.Rect(hit_x, self.owner.rect.top - 6, reach, self.owner.rect.height + 12)

        for target in targets:
            if target is self.owner or not target.stats or target.stats.hp <= 0:
                continue
            if self.swing_rect.colliderect(target.rect):
                defense = target.stats.get_def()
                damage, is_crit = self.owner.stats.roll_damage(atk_power, defense)
                target.stats.hp = max(0.0, target.stats.hp - damage)
                target.hurt_timer = 0.15
                target.last_attacker = self.owner
                if is_crit:
                    target.say("КРИТ!", 0.8)

                if target.movement:
                    dx = target.rect.centerx - self.owner.rect.centerx
                    dy = target.rect.centery - self.owner.rect.centery
                    dist = math.hypot(dx, dy)
                    if dist == 0:
                        dx, dy, dist = (-1 if self.owner.facing_left else 1), 0, 1
                    target.movement.move(dx / dist, dy / dist, 0.04, walls)
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
