import pygame
import random
from settings import TILE_SIZE

# Материалы стен (основной, тень, балки/раствор, цоколь)
WALL_STYLES = {
    "half_timber": {
        "name": "Фахверк (Штукатурка и дуб)",
        "main": (225, 215, 190),
        "shade": (195, 182, 155),
        "beam": (92, 58, 32),
        "base": (110, 115, 125),
    },
    "stone": {
        "name": "Серый тесаный камень",
        "main": (145, 150, 160),
        "shade": (110, 115, 125),
        "beam": (80, 85, 95),
        "base": (75, 80, 90),
    },
    "brick": {
        "name": "Красный кирпич",
        "main": (175, 78, 62),
        "shade": (135, 55, 42),
        "beam": (205, 195, 175),
        "base": (95, 100, 110),
    },
    "wood": {
        "name": "Бревенчатый сруб",
        "main": (148, 96, 48),
        "shade": (112, 70, 32),
        "beam": (76, 46, 20),
        "base": (100, 105, 115),
    },
}

# Материалы и цвета крыш
ROOF_STYLES = {
    "terracotta": {"main": (192, 78, 54), "light": (222, 105, 78), "dark": (138, 48, 32)},
    "slate_blue": {"main": (68, 98, 142), "light": (95, 130, 180), "dark": (42, 64, 98)},
    "moss_green": {"main": (64, 124, 72), "light": (88, 156, 96), "dark": (42, 86, 48)},
    "dark_slate": {"main": (78, 84, 98),  "light": (106, 114, 130), "dark": (50, 55, 66)},
    "straw":      {"main": (212, 180, 92), "light": (236, 206, 118), "dark": (164, 134, 58)},
}

# Настройки размеров фасада под вместимость интерьера
SIZE_PRESETS = {
    "small":  {"cols": 4, "rows": 3, "interior_cols": 10, "interior_rows": 8},
    "medium": {"cols": 5, "rows": 4, "interior_cols": 14, "interior_rows": 10},
    "large":  {"cols": 7, "rows": 4, "interior_cols": 18, "interior_rows": 12},
    "hall":   {"cols": 8, "rows": 5, "interior_cols": 22, "interior_rows": 14},
}

KIND_TITLES = {
    "tavern": "Таверна",
    "smithy": "Кузница",
    "shop":   "Лавка",
    "guild":  "Гильдия",
    "house":  "Жилой дом",
}


class GeneratedBuilding:
    def __init__(self, b_id, kind, name, tile_x, tile_y, cols, rows, sprite, wall_rects, door_rect, meta):
        self.id = b_id
        self.kind = kind
        self.name = name
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.cols = cols
        self.rows = rows
        self.rect = pygame.Rect(tile_x * TILE_SIZE, tile_y * TILE_SIZE, cols * TILE_SIZE, rows * TILE_SIZE)
        self.sprite = sprite
        self.wall_rects = wall_rects  # Прямоугольники коллизий для world.walls
        self.door_rect = door_rect    # Зона взаимодействия у двери для входа по [E]
        self.meta = meta              # Параметры (seed, стили, размер интерьера) для сохранения в БД
def _draw_roof_block(surf, rx, ry, rw, rh, roof_pal, gable_wall_pal=None):
    """Рисует объемную трапециевидную черепичную крышу со скосами и коньком"""
    outline = (22, 22, 30)
    taper = min(6, rw // 6)  # Скос крыши по бокам

    # Построчная заливка трапеции крыши
    for row in range(rh):
        progress = row / max(1, rh - 1)
        cur_taper = int(taper * (1.0 - progress))
        x1 = rx + cur_taper
        x2 = rx + rw - cur_taper
        col = roof_pal["light"] if row < 3 else (roof_pal["dark"] if row >= rh - 4 else roof_pal["main"])
        pygame.draw.line(surf, col, (x1, ry + row), (x2 - 1, ry + row), 1)

        # Ряды черепицы
        if 4 <= row < rh - 4 and row % 4 == 0:
            pygame.draw.line(surf, roof_pal["dark"], (x1 + 1, ry + row), (x2 - 2, ry + row), 1)

    # Темный контур трапеции крыши
    pts = [
        (rx + taper, ry),
        (rx + rw - taper - 1, ry),
        (rx + rw - 1, ry + rh - 1),
        (rx, ry + rh - 1),
    ]
    pygame.draw.polygon(surf, outline, pts, 1)

def _draw_wall_block(surf, wx, wy, ww, wh, wall_pal, style_key):
    """Рисует фасадную стену выбранного стиля с каменным цоколем"""
    outline = (22, 22, 30)
    pygame.draw.rect(surf, wall_pal["main"], (wx, wy, ww, wh))
    # Боковая тень справа
    pygame.draw.rect(surf, wall_pal["shade"], (wx + ww - 4, wy, 4, wh))

    if style_key == "half_timber":
        # Вертикальные и горизонтальные дубовые балки фахверка
        pygame.draw.rect(surf, wall_pal["beam"], (wx, wy, 2, wh))
        pygame.draw.rect(surf, wall_pal["beam"], (wx + ww - 2, wy, 2, wh))
        mid_y = wy + wh // 2
        pygame.draw.line(surf, wall_pal["beam"], (wx, mid_y), (wx + ww - 1, mid_y), 2)
        for bx in range(wx + 16, wx + ww - 8, 16):
            pygame.draw.line(surf, wall_pal["beam"], (bx, wy), (bx, wy + wh - 1), 2)
    elif style_key in ("stone", "brick"):
        # Кладка камня / кирпича
        step_y = 4 if style_key == "brick" else 6
        step_x = 8 if style_key == "brick" else 10
        for row_i, y in enumerate(range(wy + 3, wy + wh - 5, step_y)):
            pygame.draw.line(surf, wall_pal["shade"], (wx + 1, y), (wx + ww - 2, y), 1)
            off = (step_x // 2) if (row_i % 2 == 1) else 0
            for x in range(wx + 3 + off, wx + ww - 3, step_x):
                pygame.draw.line(surf, wall_pal["shade"], (x, y), (x, min(wy + wh - 5, y + step_y)), 1)
    elif style_key == "wood":
        # Горизонтальные бревна
        for y in range(wy + 3, wy + wh - 5, 4):
            pygame.draw.line(surf, wall_pal["shade"], (wx + 1, y), (wx + ww - 2, y), 1)

    # Каменный фундамент (цоколь) внизу
    pygame.draw.rect(surf, wall_pal["base"], (wx, wy + wh - 5, ww, 5))
    pygame.draw.rect(surf, outline, (wx, wy, ww, wh), 1)

def _draw_window(surf, x, y, lit=True, flower_box=False):
    """Рисует 8-битное окно со ставнями, переплетом и опциональным ящиком цветов"""
    outline = (22, 22, 30)
    shutter = (88, 54, 30)
    glass = (248, 218, 115) if lit else (75, 105, 140)
    pygame.draw.rect(surf, shutter, (x - 2, y, 2, 10))
    pygame.draw.rect(surf, shutter, (x + 8, y, 2, 10))
    pygame.draw.rect(surf, outline, (x, y, 8, 10))
    pygame.draw.rect(surf, glass, (x + 1, y + 1, 6, 8))
    pygame.draw.line(surf, outline, (x + 4, y + 1), (x + 4, y + 8), 1)
    pygame.draw.line(surf, outline, (x + 1, y + 5), (x + 6, y + 5), 1)

    if flower_box:
        pygame.draw.rect(surf, (110, 65, 32), (x - 1, y + 10, 10, 3))
        pygame.draw.rect(surf, (60, 155, 65), (x, y + 9, 8, 2))
        surf.set_at((x + 2, y + 9), (235, 75, 85))
        surf.set_at((x + 6, y + 9), (245, 215, 70))


def _draw_door_and_sign(surf, dx, dy, kind):
    """Рисует входную дверь с каменной аркой и вывеску на кованом кронштейне"""
    outline = (22, 22, 30)
    pygame.draw.rect(surf, (105, 110, 120), (dx - 2, dy - 2, 16, 18))
    pygame.draw.rect(surf, outline, (dx - 2, dy - 2, 16, 18), 1)
    pygame.draw.rect(surf, (118, 72, 36), (dx, dy, 12, 16))
    pygame.draw.rect(surf, (86, 50, 22), (dx + 2, dy + 2, 8, 5))
    pygame.draw.rect(surf, (86, 50, 22), (dx + 2, dy + 9, 8, 5))
    surf.set_at((dx + 9, dy + 8), (245, 210, 70))

    if kind != "house":
        # Кронштейн и табличка строго над дверью (в зоне без окон!)
        sx, sy = dx + 1, dy - 12
        pygame.draw.line(surf, outline, (dx + 6, dy - 14), (dx + 6, sy), 1)
        pygame.draw.rect(surf, outline, (sx, sy, 10, 8))
        sign_colors = {
            "tavern": (235, 175, 55),
            "smithy": (165, 175, 190),
            "shop":   (85, 195, 110),
            "guild":  (95, 160, 235),
        }
        pygame.draw.rect(surf, sign_colors.get(kind, (220, 200, 140)), (sx + 1, sy + 1, 8, 6))


def _place_section_windows(surf, sec_x, sec_w, win_y1, win_y2, door_x, has_second_floor, rng):
    """Аккуратно расставляет окна строго внутри одной секции фасада без наложений на края и вывеску"""
    margin = 7
    usable_left = sec_x + margin
    usable_right = sec_x + sec_w - margin - 8
    if usable_right < usable_left:
        return

    # Вычисляем сетку позиций окон внутри секции с шагом 18px
    positions = []
    cur_x = usable_left
    while cur_x <= usable_right:
        positions.append(cur_x)
        cur_x += 18

    # Центрируем ряд окон внутри секции
    if len(positions) > 1:
        span = positions[-1] - positions[0]
        shift = ((usable_right - usable_left) - span) // 2
        positions = [p + shift for p in positions]
    elif len(positions) == 1:
        positions = [sec_x + (sec_w - 8) // 2]

    for wx in positions:
        near_door = (door_x is not None and abs((wx + 4) - (door_x + 6)) < 15)
        # 1-й этаж: ставим окно, если оно не задевает дверь
        if not near_door:
            _draw_window(surf, wx, win_y1, lit=rng.random() < 0.8, flower_box=(rng.random() < 0.45))
        # 2-й этаж: ставим окно, если оно не перекрывает вывеску над дверью
        if has_second_floor and not near_door:
            _draw_window(surf, wx, win_y2, lit=rng.random() < 0.7, flower_box=False)


def generate_building(tile_x, tile_y, kind="house", size="medium", seed=None, building_id=None):
    rng = random.Random(seed if seed is not None else random.randint(1, 999999))
    preset = SIZE_PRESETS.get(size, SIZE_PRESETS["medium"])
    cols, rows = preset["cols"], preset["rows"]

    w_px = cols * TILE_SIZE
    h_px = rows * TILE_SIZE
    surf = pygame.Surface((w_px, h_px), pygame.SRCALPHA)

    preferred_walls = {
        "tavern": ["half_timber", "wood"],
        "smithy": ["stone", "brick"],
        "shop":   ["half_timber", "brick"],
        "guild":  ["stone", "half_timber"],
        "house":  list(WALL_STYLES.keys()),
    }
    wall_key = rng.choice(preferred_walls.get(kind, list(WALL_STYLES.keys())))
    roof_key = "dark_slate" if kind == "smithy" else rng.choice(list(ROOF_STYLES.keys()))
    wall_pal = WALL_STYLES[wall_key]
    roof_pal = ROOF_STYLES[roof_key]

    shapes = ["rect", "rect", "l_left", "l_right"]
    if cols >= 5:
        shapes.append("tower")
    shape = rng.choice(shapes)

    roof_h = max(18, int(h_px * 0.44))
    wall_y = roof_h - 2
    wall_h = h_px - wall_y
    has_2nd = (rows >= 4 and wall_h >= 34)

    # Труба на крыше
    chimney_x = rng.randint(12, w_px - 20)
    pygame.draw.rect(surf, (115, 120, 130), (chimney_x, 2, 7, 10))
    pygame.draw.rect(surf, (22, 22, 30), (chimney_x, 2, 7, 10), 1)
    surf.set_at((chimney_x + 3, 0), (220, 225, 235))

    wing_w = TILE_SIZE * 2
    door_x = w_px // 2 - 6

    if shape == "l_left" and cols >= 5:
        main_w = w_px - wing_w
        _draw_wall_block(surf, 1, wall_y, wing_w, wall_h, wall_pal, wall_key)
        _draw_roof_block(surf, 0, 4, wing_w + 1, roof_h, roof_pal)

        _draw_wall_block(surf, wing_w, wall_y, main_w - 1, wall_h - 4, wall_pal, wall_key)
        _draw_roof_block(surf, wing_w, 6, main_w, roof_h - 4, roof_pal)

        door_x = wing_w + main_w // 2 - 6
        door_y = h_px - 20
        _place_section_windows(surf, 1, wing_w, door_y + 3, wall_y + 4, None, has_2nd, rng)
        _place_section_windows(surf, wing_w, main_w - 1, door_y + 3, wall_y + 4, door_x, has_2nd, rng)
        wall_boxes = [
            pygame.Rect(tile_x * TILE_SIZE, (tile_y + 1) * TILE_SIZE, wing_w, (rows - 1) * TILE_SIZE),
            pygame.Rect(tile_x * TILE_SIZE + wing_w, (tile_y + 1) * TILE_SIZE, main_w, (rows - 1) * TILE_SIZE - 4),
        ]
    elif shape == "l_right" and cols >= 5:
        main_w = w_px - wing_w
        _draw_wall_block(surf, 1, wall_y, main_w, wall_h - 4, wall_pal, wall_key)
        _draw_roof_block(surf, 0, 6, main_w + 1, roof_h - 4, roof_pal)

        _draw_wall_block(surf, main_w, wall_y, wing_w - 1, wall_h, wall_pal, wall_key)
        _draw_roof_block(surf, main_w, 4, wing_w, roof_h, roof_pal)

        door_x = main_w // 2 - 6
        door_y = h_px - 20
        _place_section_windows(surf, 1, main_w, door_y + 3, wall_y + 4, door_x, has_2nd, rng)
        _place_section_windows(surf, main_w, wing_w - 1, door_y + 3, wall_y + 4, None, has_2nd, rng)
        wall_boxes = [
            pygame.Rect(tile_x * TILE_SIZE, (tile_y + 1) * TILE_SIZE, main_w, (rows - 1) * TILE_SIZE - 4),
            pygame.Rect(tile_x * TILE_SIZE + main_w, (tile_y + 1) * TILE_SIZE, wing_w, (rows - 1) * TILE_SIZE),
        ]
    elif shape == "tower" and cols >= 5:
        tower_w = TILE_SIZE * 2
        body_w = w_px - tower_w
        _draw_wall_block(surf, 1, wall_y + 2, body_w, wall_h - 2, wall_pal, wall_key)
        _draw_roof_block(surf, 0, 8, body_w + 1, roof_h - 6, roof_pal)

        _draw_wall_block(surf, body_w, wall_y - 4, tower_w - 1, wall_h + 4, wall_pal, wall_key)
        _draw_roof_block(surf, body_w, 1, tower_w, roof_h - 3, roof_pal)

        door_x = body_w // 2 - 6
        door_y = h_px - 16
        _place_section_windows(surf, 1, body_w, door_y + 3, wall_y + 5, door_x, has_2nd, rng)
        _place_section_windows(surf, body_w, tower_w - 1, door_y + 3, wall_y + 1, None, has_2nd, rng)
        wall_boxes = [pygame.Rect(tile_x * TILE_SIZE, (tile_y + 1) * TILE_SIZE, w_px, (rows - 1) * TILE_SIZE)]
    else:
        _draw_wall_block(surf, 1, wall_y, w_px - 2, wall_h, wall_pal, wall_key)
        _draw_roof_block(surf, 0, 4, w_px, roof_h, roof_pal)
        door_y = h_px - 16
        _place_section_windows(surf, 1, w_px - 2, door_y + 3, wall_y + 4, door_x, has_2nd, rng)
        wall_boxes = [pygame.Rect(tile_x * TILE_SIZE, (tile_y + 1) * TILE_SIZE, w_px, (rows - 1) * TILE_SIZE)]

    _draw_door_and_sign(surf, door_x, door_y, kind)

    door_world_rect = pygame.Rect(
        tile_x * TILE_SIZE + door_x - 2,
        tile_y * TILE_SIZE + door_y + 8,
        16,
        14
    )

    b_id = building_id or f"bld_{kind}_{tile_x}_{tile_y}"
    title = KIND_TITLES.get(kind, "Здание")
    meta = {
        "id": b_id,
        "kind": kind,
        "size": size,
        "seed": seed,
        "wall_style": wall_key,
        "roof_style": roof_key,
        "shape": shape,
        "interior_cols": preset["interior_cols"],
        "interior_rows": preset["interior_rows"],
    }

    return GeneratedBuilding(b_id, kind, title, tile_x, tile_y, cols, rows, surf, wall_boxes, door_world_rect, meta)