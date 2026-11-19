import pygame
import math
from settings import NATIVE_WIDTH, NATIVE_HEIGHT, TILE_SIZE

class Camera:
    def __init__(self, map_width, map_height):
        self.map_width = map_width
        self.map_height = map_height
        self.offset_x = 0
        self.offset_y = 0

    def follow(self, target):
        x = target.rect.centerx - NATIVE_WIDTH // 2
        y = target.rect.centery - NATIVE_HEIGHT // 2
        self.offset_x = int(max(0, min(self.map_width - NATIVE_WIDTH, x)))
        self.offset_y = int(max(0, min(self.map_height - NATIVE_HEIGHT, y)))

    def apply_rect(self, rect):
        return rect.move(-self.offset_x, -self.offset_y)

    def apply_pos(self, pos):
        px, py = pos
        return (px - self.offset_x, py - self.offset_y)


class WorldMap:
    def __init__(self, cols=40, rows=25):
        self.cols = cols
        self.rows = rows
        self.width = cols * TILE_SIZE
        self.height = rows * TILE_SIZE
        self.tiles = [["grass" for _ in range(cols)] for _ in range(rows)]
        self.walls = []
        self.building_plots = []
        self.entities = []
        self.projectiles = []
        self.build_town_square()

    def draw_speeches(self, screen, camera, scale, speech_font):
        if not speech_font:
            return
        for ent in self.entities:
            ent.draw_speech(screen, camera, scale, speech_font)

    def build_town_square(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.tiles[r][c] = "grass"

        lake_cx, lake_cy = 30, 17
        for r in range(self.rows):
            for c in range(self.cols):
                dist = math.hypot((c - lake_cx) * 0.85, (r - lake_cy) * 1.1)
                if dist < 3.2:
                    self.tiles[r][c] = "water"
                elif dist < 4.6:
                    self.tiles[r][c] = "sand"

        for r in range(6, 16):
            for c in range(8, 22):
                if self.tiles[r][c] != "water":
                    self.tiles[r][c] = "cobble"

        for c in range(13, 17):
            for r in range(16, self.rows - 1):
                if self.tiles[r][c] == "grass":
                    self.tiles[r][c] = "dirt"
        for r in range(10, 13):
            for c in range(22, self.cols - 1):
                if self.tiles[r][c] == "grass":
                    self.tiles[r][c] = "dirt"

        self.building_plots.append(pygame.Rect(3 * TILE_SIZE, 3 * TILE_SIZE, 5 * TILE_SIZE, 3 * TILE_SIZE))
        self.building_plots.append(pygame.Rect(23 * TILE_SIZE, 3 * TILE_SIZE, 5 * TILE_SIZE, 3 * TILE_SIZE))

        for plot in self.building_plots:
            c1, r1 = plot.x // TILE_SIZE, plot.y // TILE_SIZE
            c2, r2 = plot.right // TILE_SIZE, plot.bottom // TILE_SIZE
            for r in range(r1, r2):
                for c in range(c1, c2):
                    self.tiles[r][c] = "dirt"

        # Каменные стены по периметру
        for c in range(self.cols):
            self.tiles[0][c] = "wall"
            self.tiles[self.rows - 1][c] = "wall"
        for r in range(self.rows):
            self.tiles[r][0] = "wall"
            self.tiles[r][self.cols - 1] = "wall"


        self.walls = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.tiles[r][c] in ("wall", "water"):
                    self.walls.append(pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    def populate_town_square(self, sprites, player, db):
        """Заселяет площадь сущностями напрямую из таблицы npc_templates в БД"""
        player.respawn()
        npc_list = db.spawn_location_entities("town_square", sprites)
        self.entities = [player] + npc_list

    def update(self, dt, player, ui, loot_sprite):
        event_msg = None

        for ent in list(self.entities):
            ent.update(dt, self)

            if ent is not player and ent.stats and ent.stats.hp <= 0:
                loot_bag = ent.drop_loot_bag(loot_sprite)
                self.entities.remove(ent)
                self.entities.append(loot_bag)
                if ent.last_attacker and ent.last_attacker.stats:
                    leveled = ent.last_attacker.stats.gain_xp(50)
                    q_msgs = []
                    if getattr(ent.last_attacker, "quests", None):
                        q_msgs = ent.last_attacker.quests.on_enemy_killed(ent)

                    if ent.last_attacker is player:
                        if q_msgs:
                            event_msg = q_msgs
                        elif leveled:
                            event_msg = f"УРОВЕНЬ {player.stats.level}! Нажми C (Очков: {player.stats.stat_points})"
                        else:
                            event_msg = f"{ent.name} побежден! (+50 XP)"
                    else:
                        event_msg = f"{ent.name} пал от руки {ent.last_attacker.name}!"

        for ent in list(self.entities):
            if getattr(ent, "is_loot_bag", False) and ent.inventory:
                if len(ent.inventory.items) == 0 and ent.inventory.gold <= 0:
                    if not (ui.is_open and ui.target is ent):
                        self.entities.remove(ent)

        for proj in list(self.projectiles):
            proj.update(dt, self)
            if not proj.alive:
                self.projectiles.remove(proj)

        return event_msg

    def draw(self, surface, sprites, camera, speech_font=None):
        start_c = max(0, camera.offset_x // TILE_SIZE)
        end_c = min(self.cols, (camera.offset_x + NATIVE_WIDTH) // TILE_SIZE + 2)
        start_r = max(0, camera.offset_y // TILE_SIZE)
        end_r = min(self.rows, (camera.offset_y + NATIVE_HEIGHT) // TILE_SIZE + 2)

        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                tile_key = self.tiles[r][c]
                spr = sprites.get(tile_key, sprites.get("floor"))
                if spr:
                    surface.blit(spr, (c * TILE_SIZE - camera.offset_x, r * TILE_SIZE - camera.offset_y))

        for idx, plot in enumerate(self.building_plots):
            r_scr = camera.apply_rect(plot)
            pygame.draw.rect(surface, (160, 140, 100), r_scr, 1)
            if speech_font:
                lbl = speech_font.render(f"Место под дом #{idx + 1}", False, (210, 195, 155))
                surface.blit(lbl, (r_scr.x + 4, r_scr.y + 4))

        # Отрисовка всех сущностей с учетом смещения камеры
        for ent in sorted(self.entities, key=lambda e: e.rect.bottom):
            orig_pos = ent.rect.topleft
            ent.rect.x -= camera.offset_x
            ent.rect.y -= camera.offset_y
            if ent.combat and ent.combat.swing_rect:
                ent.combat.swing_rect.x -= camera.offset_x
                ent.combat.swing_rect.y -= camera.offset_y

            ent.draw(surface, None)

            ent.rect.topleft = orig_pos
            if ent.combat and ent.combat.swing_rect:
                ent.combat.swing_rect.x += camera.offset_x
                ent.combat.swing_rect.y += camera.offset_y

        # Отрисовка всех снарядов с учетом смещения камеры
        for proj in self.projectiles:
            proj.pos_x -= camera.offset_x
            proj.pos_y -= camera.offset_y
            proj.draw(surface)
            proj.pos_x += camera.offset_x
            proj.pos_y += camera.offset_y
