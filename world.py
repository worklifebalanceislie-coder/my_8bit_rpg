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
        # Центрируем камеру на игроке
        x = target.rect.centerx - NATIVE_WIDTH // 2
        y = target.rect.centery - NATIVE_HEIGHT // 2

        # Ограничиваем камеру границами карты
        x = max(0, min(self.map_width - NATIVE_WIDTH, x))
        y = max(0, min(self.map_height - NATIVE_HEIGHT, y))

        self.offset_x = int(x)
        self.offset_y = int(y)

    def apply_rect(self, rect):
        return rect.move(-self.offset_x, -self.offset_y)

    def apply_pos(self, pos):
        return (pos - self.offset_x, pos - self.offset_y)


class WorldMap:
    def __init__(self, cols=40, rows=25):
        self.cols = cols
        self.rows = rows
        self.width = cols * TILE_SIZE
        self.height = rows * TILE_SIZE
        self.tiles = [["grass" for _ in range(cols)] for _ in range(rows)]
        self.walls = []          # Все непроходимые препятствия (стены + вода)
        self.building_plots = [] # Размеченные площадки под будущие здания
        self.build_town_square()

    def build_town_square(self):
        # 1. Заливаем всё травой
        for r in range(self.rows):
            for c in range(self.cols):
                self.tiles[r][c] = "grass"

        # 2. Небольшое живописное озерцо с песчаным берегом в правом нижнем секторе
        lake_cx, lake_cy = 30, 17
        for r in range(self.rows):
            for c in range(self.cols):
                dist = math.hypot((c - lake_cx) * 0.85, (r - lake_cy) * 1.1)
                if dist < 3.2:
                    self.tiles[r][c] = "water"
                elif dist < 4.6:
                    self.tiles[r][c] = "sand"

        # 3. Центральная площадь из брусчатки (в центре-слева)
        for r in range(6, 16):
            for c in range(8, 22):
                if self.tiles[r][c] != "water":
                    self.tiles[r][c] = "cobble"

        # 4. Земляные дороги (от площади к озеру, на юг и на восток)
        for c in range(13, 17):
            for r in range(16, self.rows - 1):
                if self.tiles[r][c] == "grass":
                    self.tiles[r][c] = "dirt"
        for r in range(10, 13):
            for c in range(22, self.cols - 1):
                if self.tiles[r][c] == "grass":
                    self.tiles[r][c] = "dirt"

        # 5. Места под здания (фундаменты из земли/брусчатки по краям площади)
        # Место под Таверну (слева сверху)
        self.building_plots.append(pygame.Rect(3 * TILE_SIZE, 3 * TILE_SIZE, 5 * TILE_SIZE, 3 * TILE_SIZE))
        # Место под Лавку кузнеца / торговца (справа сверху от площади)
        self.building_plots.append(pygame.Rect(23 * TILE_SIZE, 3 * TILE_SIZE, 5 * TILE_SIZE, 3 * TILE_SIZE))

        for plot in self.building_plots:
            c1, r1 = plot.x // TILE_SIZE, plot.y // TILE_SIZE
            c2, r2 = plot.right // TILE_SIZE, plot.bottom // TILE_SIZE
            for r in range(r1, r2):
                for c in range(c1, c2):
                    self.tiles[r][c] = "dirt"

        # 6. Каменные стены по периметру карты + препятствия (вода)
        for c in range(self.cols):
            self.tiles[0][c] = "wall"
            self.tiles[self.rows - 1][c] = "wall"
        for r in range(self.rows):
            self.tiles[r][0] = "wall"
            self.tiles[r][self.cols - 1] = "wall"

        # Собираем все непроходимые хитбоксы (стены и вода)
        self.walls = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.tiles[r][c] in ("wall", "water"):
                    self.walls.append(pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    def draw(self, surface, sprites, camera, font=None):
        # Рисуем только те тайлы, которые попадают в объектив камеры
        start_c = max(0, camera.offset_x // TILE_SIZE)
        end_c = min(self.cols, (camera.offset_x + NATIVE_WIDTH) // TILE_SIZE + 2)
        start_r = max(0, camera.offset_y // TILE_SIZE)
        end_r = min(self.rows, (camera.offset_y + NATIVE_HEIGHT) // TILE_SIZE + 2)

        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                tile_key = self.tiles[r][c]
                spr = sprites.get(tile_key, sprites["floor"])
                screen_x = c * TILE_SIZE - camera.offset_x
                screen_y = r * TILE_SIZE - camera.offset_y
                surface.blit(spr, (screen_x, screen_y))

        # Рисуем разметку мест под будущие здания
        for idx, plot in enumerate(self.building_plots):
            r_scr = camera.apply_rect(plot)
            pygame.draw.rect(surface, (160, 140, 100), r_scr, 1)
            if font:
                lbl = font.render(f"Место под дом #{idx + 1}", False, (210, 195, 155))
                surface.blit(lbl, (r_scr.x + 4, r_scr.y + 4))
