"""world_gen.py — генератор мира: биомы, реки, озёра, города, дома, подземелья.

Модуль не трогает существующие файлы игры. Он строит обычный объект WorldMap
(или его подкласс GeneratedWorld) с тайлами, зданиями, декором и коллизиями,
поэтому его можно рисовать и обновлять через штатный игровой цикл.

Пример использования:
    sprites = load_sprites(db)
    ensure_world_sprites(sprites)              # добавить спрайты новых тайлов
    world = generate_world(cols=112, rows=68, seed=42)
    world.entities = populate_world(world, player, sprites, db)
"""
import math
import random

import pygame

from settings import TILE_SIZE, NATIVE_WIDTH, NATIVE_HEIGHT
from world import WorldMap
from building_gen import generate_building

# ---------------------------------------------------------------------------
# Шум (value noise, без внешних зависимостей)
# ---------------------------------------------------------------------------

def _hash2(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return h / 0xFFFFFFFF


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise(cols, rows, gw, gh, seed):
    """Ровный шум значений 0..1 размером cols x rows (билинейная интерполяция)."""
    grid = [[_hash2(ix, iy, seed) for ix in range(gw + 1)] for iy in range(gh + 1)]
    out = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        gy = (r / max(1, rows - 1)) * gh
        y0 = min(gh - 1, int(gy))
        fy = _smooth(gy - y0)
        for c in range(cols):
            gx = (c / max(1, cols - 1)) * gw
            x0 = min(gw - 1, int(gx))
            fx = _smooth(gx - x0)
            v00, v10 = grid[y0][x0], grid[y0][x0 + 1]
            v01, v11 = grid[y0 + 1][x0], grid[y0 + 1][x0 + 1]
            top = v00 + (v10 - v00) * fx
            bot = v01 + (v11 - v01) * fx
            out[r][c] = top + (bot - top) * fy
    return out


def fbm(cols, rows, seed, octaves=4, base_cells=5):
    """Фрактальный шум: сумма октав, каждая вдвое мельче и вдвое слабее."""
    total = [[0.0] * cols for _ in range(rows)]
    amp, norm, cells = 1.0, 0.0, base_cells
    for o in range(octaves):
        layer = value_noise(cols, rows, cells, cells, seed + o * 7919)
        for r in range(rows):
            tr = total[r]
            lr = layer[r]
            for c in range(cols):
                tr[c] += lr[c] * amp
        norm += amp
        amp *= 0.5
        cells *= 2
    for r in range(rows):
        tr = total[r]
        for c in range(cols):
            tr[c] /= norm
    return total


# ---------------------------------------------------------------------------
# Процедурные спрайты новых тайлов (существующие берутся из БД как есть)
# ---------------------------------------------------------------------------

def _tile(draw_fn, w=16, h=16):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    draw_fn(s)
    return s


def _make_snow(s):
    s.fill((232, 238, 246))
    rnd = random.Random(7)
    for _ in range(14):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (255, 255, 255))
    for _ in range(8):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (198, 212, 232))


def _make_rock(s):
    s.fill((118, 116, 112))
    rnd = random.Random(11)
    for _ in range(10):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (98, 96, 94))
    pygame.draw.line(s, (138, 136, 130), (2, 4), (9, 3), 1)
    pygame.draw.line(s, (88, 86, 84), (6, 12), (14, 14), 1)


def _make_mountain(s):
    s.fill((96, 92, 100))
    # Скальные грани
    pygame.draw.polygon(s, (124, 120, 130), [(0, 16), (5, 3), (10, 16)])
    pygame.draw.polygon(s, (74, 70, 80), [(6, 16), (11, 6), (16, 16)])
    # Снежная шапка
    pygame.draw.polygon(s, (236, 240, 248), [(4, 6), (5, 3), (7, 6), (6, 5), (5, 7)])
    pygame.draw.line(s, (50, 48, 56), (0, 15), (15, 15), 1)


def _make_swamp(s):
    s.fill((74, 96, 62))
    rnd = random.Random(23)
    for _ in range(12):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (58, 78, 50))
    # Лужица
    pygame.draw.ellipse(s, (56, 84, 74), (3, 7, 9, 6))
    pygame.draw.ellipse(s, (70, 104, 90), (4, 8, 7, 4))


def _make_mud(s):
    s.fill((96, 76, 54))
    rnd = random.Random(31)
    for _ in range(14):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (80, 62, 44))
    for _ in range(5):
        x, y = rnd.randrange(14), rnd.randrange(14)
        pygame.draw.line(s, (112, 90, 66), (x, y), (x + 2, y + 1), 1)


def _make_road(s):
    s.fill((146, 116, 82))
    rnd = random.Random(43)
    for _ in range(12):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (126, 98, 68))
    # Колеи
    pygame.draw.line(s, (112, 88, 60), (4, 0), (4, 15), 1)
    pygame.draw.line(s, (112, 88, 60), (11, 0), (11, 15), 1)


def _make_bridge(s):
    s.fill((120, 84, 48))
    for y in (0, 5, 10, 15):
        pygame.draw.line(s, (96, 66, 38), (0, y), (15, y), 1)
    pygame.draw.line(s, (146, 108, 66), (0, 2), (15, 2), 1)
    pygame.draw.line(s, (74, 50, 28), (0, 0), (0, 15), 1)
    pygame.draw.line(s, (74, 50, 28), (15, 0), (15, 15), 1)


def _make_cave_floor(s):
    s.fill((62, 60, 70))
    rnd = random.Random(57)
    for _ in range(12):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (52, 50, 60))
    pygame.draw.line(s, (78, 76, 88), (2, 9), (8, 8), 1)
    pygame.draw.line(s, (46, 44, 54), (9, 14), (15, 13), 1)


def _make_flowers(s):
    s.fill((72, 142, 74))
    rnd = random.Random(61)
    for _ in range(10):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (56, 122, 60))
    for x, y, col in ((3, 4, (235, 90, 110)), (11, 6, (245, 220, 90)),
                      (7, 12, (200, 130, 230)), (13, 13, (255, 255, 255))):
        s.set_at((x, y), col)
        s.set_at((x, y + 1), (46, 104, 52))


def _make_sand_road(s):  # грунтовая дорога по песку (запасной вариант)
    s.fill((210, 186, 130))
    rnd = random.Random(67)
    for _ in range(12):
        x, y = rnd.randrange(16), rnd.randrange(16)
        s.set_at((x, y), (190, 166, 114))


def _prop_tree(s):
    """Дуб: крона 16x16 сверху, ствол внизу (высота спрайта 24)."""
    pygame.draw.rect(s, (96, 64, 34), (6, 15, 4, 9))
    pygame.draw.rect(s, (72, 46, 24), (9, 15, 2, 9))
    pygame.draw.circle(s, (38, 92, 46), (8, 9), 7)
    pygame.draw.circle(s, (54, 122, 58), (7, 8), 6)
    pygame.draw.circle(s, (74, 150, 74), (6, 6), 4)
    s.set_at((4, 4), (96, 176, 92))
    s.set_at((11, 10), (34, 82, 42))


def _prop_pine(s):
    pygame.draw.rect(s, (96, 64, 34), (7, 17, 3, 7))
    pygame.draw.polygon(s, (30, 78, 44), [(8, 0), (1, 14), (15, 14)])
    pygame.draw.polygon(s, (44, 104, 56), [(8, 3), (3, 14), (13, 14)])
    pygame.draw.polygon(s, (60, 130, 70), [(8, 6), (4, 13), (12, 13)])


def _prop_cactus(s):
    pygame.draw.rect(s, (58, 130, 66), (6, 4, 5, 20))
    pygame.draw.rect(s, (78, 156, 86), (7, 5, 2, 18))
    pygame.draw.rect(s, (58, 130, 66), (2, 9, 4, 3))
    pygame.draw.rect(s, (58, 130, 66), (2, 5, 3, 6))
    pygame.draw.rect(s, (58, 130, 66), (11, 12, 4, 3))
    pygame.draw.rect(s, (58, 130, 66), (13, 8, 3, 6))


def _prop_bush(s):
    pygame.draw.circle(s, (46, 104, 52), (8, 11), 5)
    pygame.draw.circle(s, (62, 132, 66), (6, 10), 4)
    pygame.draw.circle(s, (80, 156, 84), (10, 9), 3)
    s.set_at((5, 7), (235, 120, 140))
    s.set_at((10, 12), (250, 230, 110))


def _prop_boulder(s):
    pygame.draw.circle(s, (96, 94, 92), (8, 10), 6)
    pygame.draw.circle(s, (124, 122, 118), (6, 8), 3)
    pygame.draw.circle(s, (72, 70, 70), (10, 12), 3)
    pygame.draw.line(s, (56, 54, 56), (2, 15), (14, 15), 1)


def _prop_cave(s):
    """Устье пещеры: скальная арка с тёмным проходом (высота 24)."""
    pygame.draw.rect(s, (88, 86, 92), (0, 6, 16, 18))
    pygame.draw.rect(s, (70, 68, 76), (0, 18, 16, 6))
    pygame.draw.ellipse(s, (10, 10, 16), (3, 6, 10, 16))
    pygame.draw.ellipse(s, (4, 4, 8), (5, 8, 6, 12))
    pygame.draw.line(s, (120, 118, 124), (1, 7), (15, 7), 1)
    s.set_at((2, 20), (58, 56, 62))
    s.set_at((13, 21), (58, 56, 62))


def _prop_gate(s):
    """Ворота города: каменные столбы, перекладина, знамя (высота 24)."""
    # Знамя между столбами
    pygame.draw.rect(s, (60, 90, 160), (4, 2, 8, 7))
    pygame.draw.rect(s, (240, 214, 96), (7, 4, 2, 3))
    # Перекладина
    pygame.draw.rect(s, (128, 124, 118), (0, 8, 16, 4))
    pygame.draw.rect(s, (94, 90, 86), (0, 11, 16, 1))
    # Столбы
    pygame.draw.rect(s, (140, 136, 130), (0, 12, 4, 12))
    pygame.draw.rect(s, (140, 136, 130), (12, 12, 4, 12))
    pygame.draw.rect(s, (104, 100, 96), (3, 12, 1, 12))
    pygame.draw.rect(s, (104, 100, 96), (11, 12, 1, 12))
    pygame.draw.rect(s, (84, 80, 78), (0, 22, 4, 2))
    pygame.draw.rect(s, (84, 80, 78), (12, 22, 4, 2))
    # Проём между столбами (тёмная тень)
    pygame.draw.rect(s, (46, 52, 44), (4, 16, 8, 8))


def _make_prop(kind):
    fns = {
        "tree": _prop_tree, "pine": _prop_pine, "cactus": _prop_cactus,
        "bush": _prop_bush, "boulder": _prop_boulder, "cave": _prop_cave,
        "gate": _prop_gate,
    }
    return _tile(fns[kind])


def ensure_world_sprites(sprites):
    """Добавляет в словарь спрайтов процедурные тайлы/декор, которых нет в БД."""
    tiles = {
        "snow": _make_snow, "rock": _make_rock, "mountain": _make_mountain,
        "swamp": _make_swamp, "mud": _make_mud, "road": _make_road,
        "bridge": _make_bridge, "cave_floor": _make_cave_floor,
        "flowers": _make_flowers, "sand_road": _make_sand_road,
    }
    for key, fn in tiles.items():
        if key not in sprites:
            sprites[key] = _tile(fn)
    for kind in ("tree", "pine", "cactus", "bush", "boulder", "cave", "gate"):
        if kind not in sprites:
            sprites[kind] = _make_prop(kind)
    _GLOBAL_SPRITES.clear()
    _GLOBAL_SPRITES.update(sprites)
    return sprites


# ---------------------------------------------------------------------------
# Биомы и вспомогательные данные
# ---------------------------------------------------------------------------

SOLID_TILES = {"water", "wall", "rock", "mountain"}

# Цвета для миникарты (по ключу тайла)
TILE_COLORS = {
    "grass": (74, 140, 74), "flowers": (96, 156, 96), "sand": (222, 198, 132),
    "dirt": (146, 110, 72), "road": (176, 142, 100), "sand_road": (232, 212, 156),
    "cobble": (150, 155, 165), "water": (54, 122, 200), "bridge": (150, 108, 64),
    "wall": (110, 114, 126), "snow": (236, 242, 250), "rock": (124, 122, 118),
    "mountain": (92, 88, 98), "swamp": (78, 100, 66), "mud": (104, 82, 58),
    "floor": (70, 70, 82), "cave_floor": (66, 64, 76),
}

BIOME_NAMES_RU = {
    "plains": "Равнины", "forest": "Лес", "desert": "Пустыня",
    "snow": "Снежные земли", "swamp": "Болото", "mountains": "Горы",
    "water": "Вода", "beach": "Побережье",
}

CITY_NAMES = [
    "Старый Дуб", "Каменный Брод", "Светлое Озеро", "Ветряной Холм",
    "Тихая Гавань", "Ржаное Поле", "Сосновый Мыс", "Янтарный Ручей",
    "Черепаший Перекат", "Белокаменный Двор",
]

PROP_KINDS = ("tree", "pine", "cactus", "bush", "boulder")


# ---------------------------------------------------------------------------
# Плавные переходы между биомами (оверлеи поверх тайлов)
# ---------------------------------------------------------------------------

# Тайлы → класс поверхности для сглаживания кромок.
# Натуральные биомы И рукотворные поверхности (дороги, площади, мосты).
BLEND_TILES = {
    "grass": "grass", "flowers": "grass",
    "sand": "sand", "water": "water",
    "snow": "snow",
    "swamp": "swamp", "mud": "swamp",
    "rock": "rock", "mountain": "rock",
    # Рукотворные поверхности
    "dirt": "dirt", "road": "road", "sand_road": "sand_road",
    "cobble": "cobble", "bridge": "bridge",
}

# Репрезентативные цвета классов (вблизи цвета самих тайлов)
TRANSITION_COLORS = {
    "grass": (74, 140, 74), "sand": (222, 198, 132), "water": (54, 122, 200),
    "snow": (236, 242, 250), "swamp": (78, 100, 66), "rock": (110, 108, 104),
    "dirt": (146, 110, 72), "road": (176, 142, 100),
    "sand_road": (232, 212, 156), "cobble": (150, 155, 165),
    "bridge": (150, 108, 64),
}

# Ранг поверхности: тайл прорисовывает цвет более «высокого» соседа на своей
# кромке (одностороннее сглаживание — без встречного перекрытия цветов).
# Рукотворные поверхности выше природных: их кромка «вытекает» на ландшафт
# (дорожка размывается в траве), вода — всегда сверху (мосты и берега).
BIOME_RANK = {
    "rock": 0, "snow": 1, "swamp": 2, "grass": 3, "sand": 4,
    "dirt": 5, "road": 6, "sand_road": 6, "cobble": 7, "bridge": 8,
    "water": 9,
}

_TRANSITION_DEPTH = 5          # ширина полосы сглаживания в пикселях
_TRANSITION_SPRITES = {}       # (класс, направление) -> Surface


def _make_transition(color, direction, seed):
    """Оверлей 16x16: цвет соседней поверхности, «вытекающий» в тайл с края
    (ребро) или из угла (диагональ), с дизерингом для органичной границы."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    rnd = random.Random(seed)
    cr, cg, cb = color
    d = _TRANSITION_DEPTH
    # Угловые пятна чуть шире рёбер: диагональ «длиннее» ребра тайла
    corner_r = _TRANSITION_DEPTH + 2
    corner_at = {"nw": (0.0, 0.0), "ne": (15.0, 0.0),
                 "sw": (0.0, 15.0), "se": (15.0, 15.0)}
    for y in range(16):
        for x in range(16):
            if direction in corner_at:
                cx, cy = corner_at[direction]
                dist = math.hypot(x - cx, y - cy)
                if dist >= corner_r:
                    continue
                a = 255.0 * (1.0 - dist / corner_r)
            else:
                if direction == "n":
                    dist = y
                elif direction == "s":
                    dist = 15 - y
                elif direction == "w":
                    dist = x
                else:  # "e"
                    dist = 15 - x
                if dist >= d:
                    continue
                a = 255.0 * (1.0 - dist / d)
            a += rnd.randint(-70, 10)   # шум кромки
            if a <= 8:
                continue
            s.set_at((x, y), (cr, cg, cb, min(255, int(a))))
    return s


def get_transition_sprite(cls, direction):
    key = (cls, direction)
    spr = _TRANSITION_SPRITES.get(key)
    if spr is None:
        spr = _make_transition(TRANSITION_COLORS[cls], direction, f"{cls}_{direction}")
        _TRANSITION_SPRITES[key] = spr
    return spr


class WorldProp:
    """Декоративный объект (дерево, куст, камень, вход в пещеру).

    Имеет тот же интерфейс, что и GeneratedBuilding (rect, sprite,
    wall_rects, door_rect, meta), поэтому попадает в world.buildings
    и рисуется вместе с персонажами с сортировкой по глубине.
    """
    def __init__(self, p_id, kind, name, rect, sprite, wall_rects,
                 door_rect=None, meta=None):
        self.id = p_id
        self.kind = kind
        self.name = name
        self.rect = rect
        self.sprite = sprite
        self.wall_rects = wall_rects
        self.door_rect = door_rect
        self.meta = meta or {}


class GeneratedWorld(WorldMap):
    """Подкласс WorldMap: базовый конструктор не рисует «площадь»,
    вместо этого запускается полная генерация мира."""
    def __init__(self, cols, rows, seed=None):
        self.seed = seed if seed is not None else random.randint(0, 2 ** 31 - 1)
        self.rng = random.Random(self.seed)
        self.biome_map = [["plains"] * cols for _ in range(rows)]
        self.cities = []
        self.dungeon_entrances = []
        self.spawn_pos = (cols * TILE_SIZE // 2, rows * TILE_SIZE // 2)
        super().__init__(cols=cols, rows=rows)
        self.building_plots = []
        self._build_minimap()

    def build_town_square(self):
        # WorldMap.__init__ вызывает этот метод — здесь строится весь мир.
        generate_overworld(self)

    def draw_ground_overlays(self, surface, camera):
        """Плавные переходы: цвет соседней поверхности вытекает в край тайла
        (рёбра) и в углы (диагональные соседи)."""
        start_c = max(0, camera.offset_x // TILE_SIZE)
        end_c = min(self.cols, (camera.offset_x + NATIVE_WIDTH) // TILE_SIZE + 2)
        start_r = max(0, camera.offset_y // TILE_SIZE)
        end_r = min(self.rows, (camera.offset_y + NATIVE_HEIGHT) // TILE_SIZE + 2)

        dirs = ((0, -1, "n"), (0, 1, "s"), (-1, 0, "w"), (1, 0, "e"))
        diag_dirs = ((-1, -1, "nw"), (1, -1, "ne"), (-1, 1, "sw"), (1, 1, "se"))
        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                cls = BLEND_TILES.get(self.tiles[r][c])
                if cls is None:
                    continue
                my_rank = BIOME_RANK[cls]
                x = c * TILE_SIZE - camera.offset_x
                y = r * TILE_SIZE - camera.offset_y
                # Собираем кандидатов и рисуем по возрастанию ранга: более
                # «высокий» сосед перекрывает более низкий (и в углах тоже).
                candidates = []
                for dc, dr, direction in dirs + diag_dirs:
                    nc, nr = c + dc, r + dr
                    if not (0 <= nc < self.cols and 0 <= nr < self.rows):
                        continue
                    n_cls = BLEND_TILES.get(self.tiles[nr][nc])
                    if n_cls is None or n_cls == cls:
                        continue
                    n_rank = BIOME_RANK[n_cls]
                    # Более «низкая» поверхность уступает: её край перекрывается
                    # цветом соседа (пляж разливается по траве и т.п.)
                    if n_rank <= my_rank:
                        continue
                    candidates.append((n_rank, get_transition_sprite(n_cls, direction)))
                candidates.sort(key=lambda item: item[0])
                for _, spr in candidates:
                    surface.blit(spr, (x, y))

    def biome_name_at(self, px, py):
        c = int(px) // TILE_SIZE
        r = int(py) // TILE_SIZE
        if not (0 <= c < self.cols and 0 <= r < self.rows):
            return "Пустота"
        for city in self.cities:
            if city["c1"] <= c <= city["c2"] and city["r1"] <= r <= city["r2"]:
                return f"Город {city['name']}"
        return BIOME_NAMES_RU.get(self.biome_map[r][c], "Земля")

    def _build_minimap(self):
        surf = pygame.Surface((self.cols, self.rows))
        for r in range(self.rows):
            for c in range(self.cols):
                col = TILE_COLORS.get(self.tiles[r][c], (74, 140, 74))
                surf.set_at((c, r), col)
        # Города — светлые точки, пещеры — тёмные
        for city in self.cities:
            pygame.draw.rect(surf, (245, 224, 150),
                             (city["c1"], city["r1"],
                              city["c2"] - city["c1"] + 1,
                              city["r2"] - city["r1"] + 1))
        for d in self.dungeon_entrances:
            surf.set_at((d["c"], d["r"]), (30, 28, 36))
        self.minimap_surface = surf


# ---------------------------------------------------------------------------
# Генерация открытого мира
# ---------------------------------------------------------------------------

def _fill_border(world, tile="mountain"):
    for c in range(world.cols):
        world.tiles[0][c] = tile
        world.tiles[world.rows - 1][c] = tile
    for r in range(world.rows):
        world.tiles[r][0] = tile
        world.tiles[r][world.cols - 1] = tile


def _gen_biomes(world, rng):
    """Базовые биомы по высоте/влаге/температуре + озёра и пляжи."""
    cols, rows = world.cols, world.rows
    seed = world.seed
    elev = fbm(cols, rows, seed, octaves=5, base_cells=4)
    moist = fbm(cols, rows, seed + 1000, octaves=4, base_cells=5)
    temp = fbm(cols, rows, seed + 2000, octaves=3, base_cells=4)

    water_level = 0.30
    mtn_level = 0.72

    for r in range(rows):
        for c in range(cols):
            e = elev[r][c]
            m = moist[r][c]
            t = temp[r][c] + (0.25 - 0.5 * r / max(1, rows - 1))  # север холоднее
            if e < water_level:
                tile, biome = "water", "water"
            elif e < water_level + 0.035:
                tile, biome = "sand", "beach"
            elif e > mtn_level:
                tile, biome = ("snow" if t < 0.42 else "mountain"), "mountains"
            elif t > 0.62 and m < 0.42:
                tile, biome = "sand", "desert"
            elif t < 0.36:
                tile, biome = "snow", "snow"
            elif m > 0.60 and e < water_level + 0.16:
                tile, biome = "swamp", "swamp"
            elif m > 0.52:
                tile, biome = "grass", "forest"
            else:
                tile, biome = "grass", "plains"
            world.tiles[r][c] = tile
            world.biome_map[r][c] = biome

    # Отдельные озёра-кляксы там, где суша
    lake_count = max(2, (cols * rows) // 2600)
    for _ in range(lake_count):
        lc = rng.randint(6, cols - 7)
        lr = rng.randint(6, rows - 7)
        rad = rng.uniform(2.2, 4.2)
        for r in range(max(1, lr - int(rad) - 2), min(rows - 1, lr + int(rad) + 3)):
            for c in range(max(1, lc - int(rad) - 2), min(cols - 1, lc + int(rad) + 3)):
                d = math.hypot((c - lc) * 0.85, (r - lr) * 1.1)
                if d < rad:
                    world.tiles[r][c] = "water"
                    world.biome_map[r][c] = "water"
                elif d < rad + 1.4 and world.tiles[r][c] in ("grass", "flowers"):
                    world.tiles[r][c] = "sand"
                    world.biome_map[r][c] = "beach"

    # Пляжи вокруг крупных водных масс (разовый проход размытия)
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if world.tiles[r][c] not in ("grass", "flowers"):
                continue
            near_water = any(world.tiles[r + dr][c + dc] == "water"
                             for dr in (-1, 0, 1) for dc in (-1, 0, 1))
            if near_water:
                world.tiles[r][c] = "sand"
                world.biome_map[r][c] = "beach"


def _gen_rivers(world, rng, count=4):
    """Реки: блуждание вниз по уклону от возвышенностей к воде/краю."""
    cols, rows = world.cols, world.rows
    starts = []
    for _ in range(count * 6):
        c = rng.randint(4, cols - 5)
        r = rng.randint(4, rows - 5)
        if world.tiles[r][c] in ("mountain", "snow", "rock"):
            starts.append((c, r))
        if len(starts) >= count:
            break
    while len(starts) < count:
        starts.append((rng.randint(4, cols - 5), rng.randint(4, rows - 5)))

    for sc, sr in starts:
        c, r = sc, sr
        for _ in range(cols + rows):
            if not (1 <= c < cols - 1 and 1 <= r < rows - 1):
                break
            if world.tiles[r][c] == "water":
                break
            if world.tiles[r][c] not in ("mountain", "rock", "snow"):
                world.tiles[r][c] = "water"
                world.biome_map[r][c] = "water"
                # Немного расширяем русло
                if rng.random() < 0.45 and 1 <= r + 1 < rows - 1:
                    world.tiles[r + 1][c] = "water"
                    world.biome_map[r + 1][c] = "water"
            # Ищем соседа пониже (со случайным уклоном вбок)
            best, best_e = None, 1e9
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
                nc, nr = c + dc, r + dr
                if 1 <= nc < cols - 1 and 1 <= nr < rows - 1:
                    e = _hash2(nc, nr, world.seed + 5000)
                    if world.tiles[nr][nc] == "water":
                        e -= 5
                    if e < best_e:
                        best_e, best = e, (nc, nr)
            if best is None:
                break
            c, r = best


def _terrain_ok_for_city(world, c, r, radius):
    """Проверяет, что участок достаточно ровный и не залит водой."""
    water = mtn = 0
    total = 0
    for rr in range(r - radius, r + radius + 1):
        for cc in range(c - radius, c + radius + 1):
            if not (1 <= cc < world.cols - 1 and 1 <= rr < world.rows - 1):
                return False
            t = world.tiles[rr][cc]
            total += 1
            if t == "water":
                water += 1
            elif t in ("mountain", "rock"):
                mtn += 1
    return water < total * 0.12 and mtn < total * 0.10


def _pick_city_sites(world, rng, want=4):
    cols, rows = world.cols, world.rows
    sites, attempts = [], 0
    while len(sites) < want and attempts < want * 60:
        attempts += 1
        c = rng.randint(8, cols - 9)
        r = rng.randint(8, rows - 9)
        radius = 7 if len(sites) == 0 else rng.randint(5, 7)
        if world.biome_map[r][c] in ("water", "mountains", "swamp"):
            continue
        if not _terrain_ok_for_city(world, c, r, radius):
            continue
        if any(math.hypot(c - s[0], r - s[1]) < 16 for s in sites):
            continue
        sites.append((c, r, radius))
    return sites


def _carve_city_ground(world, c, r, radius):
    """Сравнять участок: суша под городом становится травой/землёй."""
    for rr in range(r - radius, r + radius + 1):
        for cc in range(c - radius, c + radius + 1):
            if 1 <= cc < world.cols - 1 and 1 <= rr < world.rows - 1:
                t = world.tiles[rr][cc]
                if t in ("water", "mountain", "rock", "snow", "swamp", "sand"):
                    if t == "sand":
                        world.tiles[rr][cc] = "dirt"
                    else:
                        world.tiles[rr][cc] = "grass"
                    world.biome_map[rr][cc] = "plains"


def _place_buildings_in_city(world, rng, city):
    """Расставляет здания по периметру площади города.
    Возвращает множество тайлов, занятых зданиями."""
    c, r = city["c"], city["r"]
    pr1, pr2 = city["pr1"], city["pr2"]
    pc1, pc2 = city["pc1"], city["pc2"]
    plans = []

    if city["size"] == "big":
        plans = [("tavern", "large"), ("smithy", "medium"), ("shop", "medium"),
                 ("guild", "medium")]
        houses = 6
    elif city["size"] == "town":
        plans = [("tavern", "medium"), ("smithy", "small"), ("shop", "small")]
        houses = 4
    else:
        plans = [("tavern", "small")]
        houses = 3

    # Слоты: ряды над площадью и под площадью, колонки по бокам
    slots = []
    for cc in range(pc1 - 2, pc2 - 1):
        slots.append((cc, pr1 - 4, "row_up"))
        slots.append((cc, pr2 + 2, "row_down"))
    for rr in range(pr1 - 1, pr2):
        slots.append((pc1 - 7, rr, "col_left"))
        slots.append((pc2 + 3, rr, "col_right"))

    rng.shuffle(slots)
    used = set()
    plan_i = 0
    max_buildings = len(plans) + houses
    for (sc, sr, _side) in slots:
        if plan_i >= max_buildings:
            break
        # План сгорает только если здание действительно поставили
        if plan_i < len(plans):
            kind, size = plans[plan_i]
        else:
            kind, size = "house", rng.choice(["small", "medium"])

        from building_gen import SIZE_PRESETS
        preset = SIZE_PRESETS[size]
        bc, br = preset["cols"], preset["rows"]
        tile_x = sc - bc // 2
        tile_y = sr
        if _side in ("col_left", "col_right"):
            tile_x = sc
            tile_y = sr - br // 2
        footprint = {(tile_x + i, tile_y + j) for i in range(bc) for j in range(br)}
        if any(p in used for p in footprint):
            continue
        if any(not (1 <= p[0] < world.cols - 2 and 1 <= p[1] < world.rows - 3)
               for p in footprint):
            continue
        # Не заезжаем на площадь, воду и друг на друга
        if any(world.tiles[p[1]][p[0]] in ("water", "cobble", "bridge",
                                            "mountain", "rock")
               for p in footprint):
            continue
        used |= footprint
        plan_i += 1

        bld = generate_building(tile_x=tile_x, tile_y=tile_y, kind=kind,
                                size=size, seed=rng.randint(1, 999999),
                                building_id=f"bld_{city['name']}_{kind}_{tile_x}_{tile_y}")
        world.buildings.append(bld)
        for p in footprint:
            world.tiles[p[1]][p[0]] = "dirt"
    return used


def _build_city(world, rng, idx, c, r, radius):
    """Город на поверхности: площадь, дороги и ВОРОТА.

    Здания и жители теперь живут в отдельной локации (generate_city),
    сюда ставится только вход-арка с зоной взаимодействия [E].
    """
    size = "big" if idx == 0 else ("town" if idx <= 2 else "village")
    _carve_city_ground(world, c, r, radius + 3)

    # Площадь-плаза из брусчатки
    pr1, pr2 = r - 2, r + 2
    pc1, pc2 = c - 3, c + 3
    for rr in range(pr1, pr2 + 1):
        for cc in range(pc1, pc2 + 1):
            world.tiles[rr][cc] = "cobble"
            world.biome_map[rr][cc] = "plains"

    name = CITY_NAMES[idx % len(CITY_NAMES)]
    city = {
        "name": name, "idx": idx, "c": c, "r": r, "radius": radius, "size": size,
        "pr1": pr1, "pr2": pr2, "pc1": pc1, "pc2": pc2,
        "c1": c - radius, "c2": c + radius, "r1": r - radius, "r2": r + radius,
    }
    world.cities.append(city)

    # Ворота-арка в центре площади — вход в отдельную локацию города
    spr = _GLOBAL_SPRITES.get("gate")
    if spr is None:
        spr = _make_prop("gate")
    h = spr.get_height()
    rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE + TILE_SIZE - h,
                       spr.get_width(), h)
    door = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    gate = WorldProp(f"gate_{idx}", "city_gate", f"Ворота: {name}",
                     rect, spr, [], door_rect=door,
                     meta={"city_idx": idx, "size": size, "name": name})
    world.buildings.append(gate)

    # Дорожки от площади к краям города (к воротам ведут дороги)
    def lay_road(rr, cc):
        t = world.tiles[rr][cc]
        if t not in ("cobble", "water", "bridge", "dirt"):
            world.tiles[rr][cc] = "road"

    for cc in range(pc1, pc2 + 1):
        for rr in range(r - radius, pr1):
            lay_road(rr, cc)
        for rr in range(pr2 + 1, r + radius + 1):
            lay_road(rr, cc)
    for rr in range(pr1, pr2 + 1):
        for cc in range(c - radius, pc1):
            lay_road(rr, cc)
        for cc in range(pc2 + 1, c + radius + 1):
            lay_road(rr, cc)

    return city


def _connect_cities(world, rng, cities):
    """Дороги между городами: простой путь с обходом воды (мосты) и гор."""
    for i in range(len(cities) - 1):
        a, b = cities[i], cities[i + 1]
        c, r = a["c"], a["r"]
        gc, gr = b["c"], b["r"]
        guard = 0
        while (c, r) != (gc, gr) and guard < world.cols + world.rows:
            guard += 1
            if world.tiles[r][c] in ("cobble",):
                pass
            elif world.tiles[r][c] == "water":
                world.tiles[r][c] = "bridge"
                world.biome_map[r][c] = "water"
            elif world.tiles[r][c] not in ("mountain", "rock", "snow"):
                world.tiles[r][c] = "road"
            # Шаг к цели с небольшим случайным уклоном
            dx = gc - c
            dy = gr - r
            if abs(dx) > abs(dy):
                step = (1 if dx > 0 else -1, 0 if rng.random() < 0.8 else
                        (1 if dy >= 0 else -1))
            else:
                step = (0 if rng.random() < 0.8 else (1 if dx >= 0 else -1),
                        1 if dy > 0 else -1)
            nc, nr = c + step[0], r + step[1]
            if 1 <= nc < world.cols - 1 and 1 <= nr < world.rows - 1:
                c, r = nc, nr


def _in_city(world, c, r, pad=2):
    for city in world.cities:
        if (city["c1"] - pad <= c <= city["c2"] + pad and
                city["r1"] - pad <= r <= city["r2"] + pad):
            return True
    return False


def _scatter_decor(world, sprites, rng):
    """Деревья/кусты/камни по биомам + входы в пещеры."""
    cols, rows = world.cols, world.rows
    props = []
    tree_id = 0

    density = {"forest": 0.10, "plains": 0.018, "snow": 0.06,
               "desert": 0.02, "swamp": 0.05, "mountains": 0.03,
               "beach": 0.008}
    prop_for_biome = {
        "forest": [("tree", 0.75), ("bush", 0.25)],
        "plains": [("bush", 0.5), ("tree", 0.3), ("boulder", 0.2)],
        "snow": [("pine", 0.8), ("boulder", 0.2)],
        "desert": [("cactus", 0.7), ("boulder", 0.3)],
        "swamp": [("tree", 0.5), ("bush", 0.5)],
        "mountains": [("boulder", 0.7), ("pine", 0.3)],
        "beach": [("boulder", 1.0)],
    }

    for r in range(2, rows - 2):
        for c in range(2, cols - 2):
            tile = world.tiles[r][c]
            if tile in SOLID_TILES or tile in ("road", "cobble", "dirt", "bridge"):
                continue
            if _in_city(world, c, r, pad=1):
                continue
            biome = world.biome_map[r][c]
            if rng.random() >= density.get(biome, 0.01):
                continue
            kind = rng.choices([k for k, _ in prop_for_biome.get(biome, [("bush", 1.0)])],
                               weights=[w for _, w in prop_for_biome.get(biome, [("bush", 1.0)])])[0]
            spr = sprites.get(kind)
            if spr is None:
                continue
            h = spr.get_height()
            rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE + TILE_SIZE - h,
                               spr.get_width(), h)
            # Непроходим только ствол/основание
            trunk = pygame.Rect(c * TILE_SIZE + 4, r * TILE_SIZE + TILE_SIZE - 8,
                                8, 8)
            p = WorldProp(f"prop_{kind}_{tree_id}", kind, kind, rect, spr, [trunk])
            props.append(p)
            tree_id += 1

    # Декор на пляжах/болоте без биома-плотности уже покрыт; ставим пещеры
    cave_spots = []
    seen_spots = set()
    for _ in range(60):
        c = rng.randint(3, cols - 4)
        r = rng.randint(3, rows - 4)
        if (c, r) in seen_spots:
            continue
        if world.tiles[r][c] in ("mountain", "rock", "snow") and not _in_city(world, c, r, 3):
            # Подходим к пещере снизу: тайл под горой должен быть проходим
            below = r + 1
            if below < rows - 1 and world.tiles[below][c] not in SOLID_TILES:
                cave_spots.append((c, r))
                seen_spots.add((c, r))
                if len(cave_spots) >= 4:
                    break

    for i, (c, r) in enumerate(cave_spots):
        spr = sprites.get("cave")
        h = spr.get_height()
        rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE + TILE_SIZE - h,
                           spr.get_width(), h)
        door = pygame.Rect(c * TILE_SIZE, (r + 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        meta = {"depth": i + 1, "cave_c": c, "cave_r": r}
        p = WorldProp(f"cave_{i}", "cave", "Пещера", rect, spr,
                      [pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)],
                      door_rect=door, meta=meta)
        props.append(p)
        world.dungeon_entrances.append({"c": c, "r": r, "id": p.id, "depth": i + 1})

    world.buildings.extend(props)


def _build_walls(world):
    """Коллизии: твёрдые тайлы + стены зданий + основания декора."""
    walls = []
    for r in range(world.rows):
        for c in range(world.cols):
            if world.tiles[r][c] in SOLID_TILES:
                walls.append(pygame.Rect(c * TILE_SIZE, r * TILE_SIZE,
                                         TILE_SIZE, TILE_SIZE))
    for bld in getattr(world, "buildings", []):
        walls.extend(bld.wall_rects)
    world.walls = walls


def generate_overworld(world):
    """Полный конвейер генерации открытого мира (вызывается из конструктора)."""
    rng = world.rng
    _gen_biomes(world, rng)
    _gen_rivers(world, rng, count=3 + (world.cols * world.rows) // 4000)
    _fill_border(world, "mountain")

    sites = _pick_city_sites(world, rng, want=4)
    if not sites:
        # Фолбэк: центр карты всегда пригоден для города
        sites = [(world.cols // 2, world.rows // 2, 6)]
    cities = []
    for idx, (c, r, radius) in enumerate(sites):
        cities.append(_build_city(world, rng, idx, c, r, radius))
    _connect_cities(world, rng, cities)

    # Декору нужны спрайты — берём из глобального кэша (ensure_world_sprites)
    _scatter_decor(world, _GLOBAL_SPRITES, rng)

    _build_walls(world)

    # Точка возрождения — площадь первого города
    cap = cities[0]
    world.spawn_pos = (cap["c"] * TILE_SIZE, (cap["r"] + 2) * TILE_SIZE)
    return world


# Словарь спрайтов, заполняемый через ensure_world_sprites() — нужен декору.
_GLOBAL_SPRITES = {}


def generate_world(cols=112, rows=68, seed=None):
    """Создаёт новый GeneratedWorld заданного размера."""
    return GeneratedWorld(cols=cols, rows=rows, seed=seed)


# ---------------------------------------------------------------------------
# Население мира
# ---------------------------------------------------------------------------

def _find_free_tile(world, c, r, tries=40):
    """Ищет проходимый тайл рядом с (c, r) спиралью."""
    if 1 <= c < world.cols - 1 and 1 <= r < world.rows - 1:
        if world.tiles[r][c] not in SOLID_TILES:
            return c, r
    for rad in range(1, tries):
        for dc in range(-rad, rad + 1):
            for dr in (-rad, rad):
                nc, nr = c + dc, r + dr
                if (1 <= nc < world.cols - 1 and 1 <= nr < world.rows - 1
                        and world.tiles[nr][nc] not in SOLID_TILES):
                    return nc, nr
        for dr in range(-rad, rad + 1):
            for dc in (-rad, rad):
                nc, nr = c + dc, r + dr
                if (1 <= nc < world.cols - 1 and 1 <= nr < world.rows - 1
                        and world.tiles[nr][nc] not in SOLID_TILES):
                    return nc, nr
    return c, r


def populate_world(world, player, sprites, db, monsters=14):
    """Заселяет поверхность: монстры и сундуки в диких биомах.

    Жители городов живут в отдельных локациях (generate_city).
    """
    from components.inventory import Inventory
    from entities import Entity
    from items import ITEMS_DB
    from monster_gen import generate_monster

    world.entities = [player]

    # Монстры в диких биомах (подальше от городов)
    placed = 0
    guard = 0
    while placed < monsters and guard < monsters * 40:
        guard += 1
        c = world.rng.randint(2, world.cols - 3)
        r = world.rng.randint(2, world.rows - 3)
        if world.tiles[r][c] in SOLID_TILES or _in_city(world, c, r, pad=4):
            continue
        mob = generate_monster(c * TILE_SIZE, r * TILE_SIZE, sprites, db=db)
        world.entities.append(mob)
        placed += 1

    # 4. Сундуки с добычей в диких местах
    for _ in range(6):
        c = world.rng.randint(2, world.cols - 3)
        r = world.rng.randint(2, world.rows - 3)
        if world.tiles[r][c] in SOLID_TILES or _in_city(world, c, r, pad=2):
            continue
        chest = Entity("Дикий сундук", c * TILE_SIZE, r * TILE_SIZE,
                       (180, 120, 60), sprite=sprites.get("chest"),
                       is_container=True)
        chest.inventory = Inventory(capacity=12,
                                    gold=world.rng.randint(20, 200))
        for iid in world.rng.sample(list(ITEMS_DB.keys()),
                                    k=min(3, len(ITEMS_DB))):
            chest.inventory.add_item(ITEMS_DB[iid])
        world.entities.append(chest)

    # Игрок стартует у ворот столицы (чуть ниже арки)
    if world.cities:
        sc, sr = _find_free_tile(world, world.cities[0]["c"],
                                 world.cities[0]["r"] + 2)
        player.rect.topleft = (sc * TILE_SIZE, sr * TILE_SIZE)
        if player.movement:
            player.movement.pos_x = float(player.rect.x)
            player.movement.pos_y = float(player.rect.y)
    return world.entities


# ---------------------------------------------------------------------------
# Города как отдельные локации (аналог интерьеров)
# ---------------------------------------------------------------------------

class CityLocation(WorldMap):
    """Отдельная локация города/деревни: площадь, здания, жители, выход."""
    def __init__(self, city, cols, rows, return_pos, sprites):
        self.city = city
        self.return_pos = return_pos
        self.exit_rect = None
        self.interactive_props = []
        self.spawn_pos = ((cols // 2) * TILE_SIZE, (rows - 3) * TILE_SIZE)
        super().__init__(cols=cols, rows=rows)
        self.building_plots = []

    def build_town_square(self):
        pass  # карта строится в generate_city

    # Те же плавные переходы травы/дорожек, что и на поверхности
    draw_ground_overlays = GeneratedWorld.draw_ground_overlays

    def redraw_minimap(self):
        """Перестроить мини-модель после генерации (тайлы/здания/выход)."""
        surf = pygame.Surface((self.cols, self.rows))
        for r in range(self.rows):
            for c in range(self.cols):
                surf.set_at((c, r), TILE_COLORS.get(self.tiles[r][c],
                                                    (74, 140, 74)))
        # Здания — тёмные блоки с светлой крышей
        for bld in self.buildings:
            r1 = max(0, bld.rect.y // TILE_SIZE)
            c1 = max(0, bld.rect.x // TILE_SIZE)
            r2 = min(self.rows - 1, (bld.rect.bottom - 1) // TILE_SIZE)
            c2 = min(self.cols - 1, (bld.rect.right - 1) // TILE_SIZE)
            for rr in range(r1, r2 + 1):
                for cc in range(c1, c2 + 1):
                    surf.set_at((cc, rr), (60, 56, 70))
        # Выход — яркая метка внизу
        if self.exit_rect:
            ec = int(self.exit_rect.centerx) // TILE_SIZE
            er = int(self.exit_rect.centery) // TILE_SIZE
            if 0 <= ec < self.cols and 0 <= er < self.rows:
                for dc in (-1, 0, 1):
                    if 0 <= ec + dc < self.cols:
                        surf.set_at((ec + dc, er), (90, 220, 120))
        self.minimap_surface = surf


CITY_LOCATION_SIZES = {
    "big": (48, 32), "town": (38, 26), "village": (28, 20),
}


def generate_city(city, sprites, return_pos, db=None, rng=None):
    """Генерирует отдельную локацию города: площадь, здания, жители, выход.

    Возвращает CityLocation — рисуется и обновляется как обычная карта,
    выход [E] у нижних ворот возвращает в return_pos на поверхности.
    """
    from components.inventory import Inventory
    from components.stats import Stats
    from components.ai import AIController
    from entities import Entity
    from items import ITEMS_DB

    rng = rng or random.Random(hash(city["name"]) & 0xFFFFFFFF)
    cols, rows = CITY_LOCATION_SIZES.get(city["size"], (38, 26))
    loc = CityLocation(city, cols, rows, return_pos, sprites or {})
    tiles = loc.tiles

    # 1) Трава + каменный забор по периметру
    for r in range(rows):
        for c in range(cols):
            tiles[r][c] = "grass"
    for c in range(cols):
        tiles[0][c] = "wall"
        tiles[rows - 1][c] = "wall"
    for r in range(rows):
        tiles[r][0] = "wall"
        tiles[r][cols - 1] = "wall"

    # 2) Площадь-плаза в центре
    c, r = cols // 2, rows // 2
    pr1, pr2 = r - 2, r + 2
    pc1, pc2 = c - 3, c + 3
    for rr in range(pr1, pr2 + 1):
        for cc in range(pc1, pc2 + 1):
            tiles[rr][cc] = "cobble"

    # 3) Здания вокруг площади (та же раскладка, что и раньше)
    spec = dict(city)
    spec.update({"c": c, "r": r, "pr1": pr1, "pr2": pr2,
                 "pc1": pc1, "pc2": pc2})
    used = _place_buildings_in_city(loc, rng, spec)

    # 4) Дороги от площади к краям, вниз — к выходным воротам
    def lay_road(rr, cc):
        if (rr, cc) in used:
            return
        t = tiles[rr][cc]
        if t not in ("cobble", "water", "bridge", "dirt", "wall"):
            tiles[rr][cc] = "road"

    for cc in range(pc1, pc2 + 1):
        for rr in range(1, pr1):
            lay_road(rr, cc)
        for rr in range(pr2 + 1, rows - 1):
            lay_road(rr, cc)
    for rr in range(pr1, pr2 + 1):
        for cc in range(1, pc1):
            lay_road(rr, cc)
        for cc in range(pc2 + 1, cols - 1):
            lay_road(rr, cc)

    # 5) Выходные ворота внизу (проеем в заборе)
    door_c = c
    tiles[rows - 1][door_c] = "road"
    tiles[rows - 2][door_c] = "road"
    loc.exit_rect = pygame.Rect(door_c * TILE_SIZE - 8,
                                (rows - 1) * TILE_SIZE - 4,
                                TILE_SIZE + 16, TILE_SIZE + 8)
    loc.spawn_pos = (door_c * TILE_SIZE, (rows - 3) * TILE_SIZE)

    # 6) Жители: столица — жители из БД, прочие города — торговец
    if city.get("idx", 0) == 0 and db is not None:
        offset_x = c * TILE_SIZE - 240
        offset_y = r * TILE_SIZE - 180
        for ent in db.spawn_location_entities("town_square", sprites or {}):
            ent.rect.x += offset_x
            ent.rect.y += offset_y
            nc, nr = _find_free_tile(loc, ent.rect.x // TILE_SIZE,
                                     ent.rect.y // TILE_SIZE)
            ent.rect.topleft = (nc * TILE_SIZE, nr * TILE_SIZE)
            if ent.movement:
                ent.movement.pos_x = float(ent.rect.x)
                ent.movement.pos_y = float(ent.rect.y)
            loc.entities.append(ent)
    else:
        nc, nr = _find_free_tile(loc, c, r + 1)
        merch = Entity(f"Торговец ({city['name']})", nc * TILE_SIZE,
                       nr * TILE_SIZE, (230, 190, 65),
                       sprite=(sprites or {}).get("npc"), faction="free_city",
                       sprite_bank=sprites)
        merch.stats = Stats(hp=90, mp=30, str_val=4, end_val=4)
        merch.inventory = Inventory(capacity=30, gold=2000)
        for iid in ("potion", "mana_potion", "iron_sword", "herb_leaf", "gem"):
            if iid in ITEMS_DB:
                merch.inventory.add_item(ITEMS_DB[iid])
        merch.ai = AIController(merch, role="merchant", aggro_radius=0)
        merch.dialogue = {
            "greeting": f"Добро пожаловать в {city['name']}!",
            "rumor": "В пещерах у гор лежат сокровища и опасные твари.",
        }
        merch.link_components()
        loc.entities.append(merch)

        # Страж у площади
        gc, gr = _find_free_tile(loc, c - 4, r)
        guard = Entity(f"Страж ({city['name']})", gc * TILE_SIZE,
                       gr * TILE_SIZE, (120, 140, 180),
                       sprite=(sprites or {}).get("guard"), faction="town",
                       sprite_bank=sprites)
        guard.stats = Stats(hp=140, mp=20, str_val=7, end_val=6)
        guard.ai = AIController(guard, role="guard", aggro_radius=0)
        guard.link_components()
        loc.entities.append(guard)

    # 7) Декор: пара кустов у стен
    for _ in range(6):
        dc = rng.randint(2, cols - 3)
        dr = rng.randint(2, rows - 4)
        if tiles[dr][dc] != "grass" or (dc, dr) in used:
            continue
        spr = (sprites or {}).get("bush")
        if spr is None:
            continue
        h = spr.get_height()
        rect = pygame.Rect(dc * TILE_SIZE, dr * TILE_SIZE + TILE_SIZE - h,
                           spr.get_width(), h)
        loc.buildings.append(WorldProp(
            f"city_bush_{dc}_{dr}", "bush", "bush", rect, spr,
            [pygame.Rect(dc * TILE_SIZE + 4, dr * TILE_SIZE + TILE_SIZE - 8,
                         8, 8)]))

    # 8) Коллизии: твёрдые тайлы + стены зданий
    _build_walls(loc)
    # 9) Мини-модель города для миникарты (раскладка, здания, выход)
    loc.redraw_minimap()
    return loc


# ---------------------------------------------------------------------------
# Подземелья
# ---------------------------------------------------------------------------

class DungeonRoom(WorldMap):
    """Карта подземелья: коридоры и комнаты, монстры, сундуки, выход."""
    def __init__(self, depth, cols, rows, return_pos, sprites):
        self.depth = depth
        self.return_pos = return_pos
        self.exit_rect = None
        self.interactive_props = []
        self.spawn_pos = (TILE_SIZE * 2, rows * TILE_SIZE - TILE_SIZE * 3)
        super().__init__(cols=cols, rows=rows)
        self.building_plots = []

    def build_town_square(self):
        pass  # карта строится в generate_dungeon


def generate_dungeon(depth=1, return_pos=(0, 0), sprites=None, db=None,
                     rng=None, size=28):
    """Генерирует карту подземелья с лестницей-выходом и комнатами."""
    from entities import Entity
    from components.inventory import Inventory
    from components.stats import Stats
    from components.ai import AIController
    from components.combat import Combat
    from components.skills import SkillBook
    from items import ITEMS_DB
    from monster_gen import generate_monster

    rng = rng or random.Random()
    cols, rows = size, int(size * 0.65)
    room = DungeonRoom(depth, cols, rows, return_pos, sprites or {})
    tiles = room.tiles

    # Заливаем камнем
    for r in range(rows):
        for c in range(cols):
            tiles[r][c] = "wall"

    # Комнаты
    rooms = []
    for _ in range(6 + depth * 2):
        w = rng.randint(4, 8)
        h = rng.randint(3, 6)
        rc = rng.randint(1, cols - w - 2)
        rr = rng.randint(1, rows - h - 2)
        rooms.append((rc, rr, w, h))
        for r in range(rr, rr + h):
            for c in range(rc, rc + w):
                tiles[r][c] = "cave_floor"

    # Коридоры между центрами комнат (по порядку)
    centers = [(rc + w // 2, rr + h // 2) for rc, rr, w, h in rooms]
    for i in range(len(centers) - 1):
        (c1, r1), (c2, r2) = centers[i], centers[i + 1]
        for c in range(min(c1, c2), max(c1, c2) + 1):
            if 0 < r1 < rows - 1 and tiles[r1][c] == "wall":
                tiles[r1][c] = "cave_floor"
        for r in range(min(r1, r2), max(r1, r2) + 1):
            if 0 < c2 < cols - 1 and tiles[r][c2] == "wall":
                tiles[r][c2] = "cave_floor"

    # Стартовая позиция — центр первой комнаты, к ней же тянется коридор к выходу
    if centers:
        sc, sr = centers[0]
    else:
        sc, sr = cols // 2, rows // 2
    room.spawn_pos = (sc * TILE_SIZE, sr * TILE_SIZE)

    # Выход — лестница внизу карты, соединённая коридором с первой комнатой
    exit_c = sc
    exit_r = rows - 2
    for r in range(sr, rows - 1):
        for c in (exit_c, exit_c - 1, exit_c + 1):
            if 0 < c < cols - 1 and tiles[r][c] == "wall":
                tiles[r][c] = "cave_floor"
    for r in (rows - 2, rows - 3):
        if 0 < exit_c < cols - 1:
            tiles[r][exit_c] = "cobble"
    room.exit_rect = pygame.Rect(exit_c * TILE_SIZE - 8,
                                 (rows - 2) * TILE_SIZE - 4,
                                 TILE_SIZE + 16, TILE_SIZE + 8)

    # Стены-коллизии
    room.walls = [pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                  for r in range(rows) for c in range(cols)
                  if tiles[r][c] == "wall"]

    # Монстры в комнатах (кроме стартовой)
    for (rc, rr, w, h) in rooms[1:]:
        for _ in range(1 + depth // 2):
            c = rng.randint(rc, rc + w - 1)
            r = rng.randint(rr, rr + h - 1)
            if tiles[r][c] != "cave_floor":
                continue
            if rng.random() < 0.7:
                mob = generate_monster(c * TILE_SIZE, r * TILE_SIZE,
                                       sprites or {}, db=db)
                mob.stats.hp += depth * 8
                mob.stats.str += depth
                room.entities.append(mob)

    # Сундуки
    for (rc, rr, w, h) in rng.sample(rooms, k=min(2, len(rooms))):
        c, r = rc + w // 2, rr + h // 2
        if tiles[r][c] != "cave_floor":
            continue
        chest = Entity(f"Сундук подземелья {depth}", c * TILE_SIZE,
                       r * TILE_SIZE, (180, 120, 60),
                       sprite=(sprites or {}).get("chest"), is_container=True)
        chest.inventory = Inventory(capacity=12,
                                    gold=rng.randint(50, 150 + depth * 60))
        pool = list(ITEMS_DB.keys())
        for iid in rng.sample(pool, k=min(2 + depth, len(pool))):
            chest.inventory.add_item(ITEMS_DB[iid])
        room.entities.append(chest)

    # Страж у выхода на глубоких уровнях
    if depth >= 2 and rooms:
        rc, rr, w, h = rooms[-1]
        boss = generate_monster((rc + w // 2) * TILE_SIZE,
                                (rr + h // 2) * TILE_SIZE, sprites or {}, db=db)
        boss.name = f"Хранитель глубин {depth}"
        if boss.stats:
            boss.stats.hp += depth * 20
            boss.stats.str += depth * 2
        room.entities.append(boss)

    return room
