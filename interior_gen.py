import pygame
import random
from settings import TILE_SIZE
from world import WorldMap
from entities import Entity
from components.inventory import Inventory
from components.stats import Stats
from components.ai import AIController
from items import ITEMS_DB
from appearance import build_character_sprite, generate_random_appearance

_INTERIOR_SPRITES = {}

def get_interior_sprites():
    """Генерирует 16x16 спрайты мебели и полов для интерьеров (кэшируются один раз)"""
    if _INTERIOR_SPRITES:
        return _INTERIOR_SPRITES

    def make_tile(draw_fn):
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        draw_fn(s)
        return s

    # 1. Деревянный пол (доски)
    def draw_wood_floor(s):
        s.fill((128, 84, 46))
        for y in (0, 8):
            pygame.draw.line(s, (92, 56, 28), (0, y), (15, y), 1)
            pygame.draw.line(s, (148, 102, 58), (0, y + 1), (15, y + 1), 1)
        pygame.draw.line(s, (92, 56, 28), (7, 0), (7, 7), 1)
        pygame.draw.line(s, (92, 56, 28), (13, 8), (13, 15), 1)

    # 2. Каменный пол (плиты)
    def draw_stone_floor(s):
        s.fill((105, 110, 120))
        pygame.draw.rect(s, (122, 128, 140), (1, 1, 6, 6))
        pygame.draw.rect(s, (122, 128, 140), (9, 9, 6, 6))
        pygame.draw.line(s, (75, 80, 90), (0, 8), (15, 8), 1)
        pygame.draw.line(s, (75, 80, 90), (8, 0), (8, 15), 1)

    # 3. Ковер (красный с золотой каймой)
    def draw_carpet(s):
        s.fill((165, 48, 48))
        pygame.draw.rect(s, (225, 180, 65), (1, 1, 14, 14), 1)

    # 4. Деревянный стол / Прилавок
    def draw_table(s):
        pygame.draw.rect(s, (22, 22, 30), (1, 3, 14, 11))
        pygame.draw.rect(s, (158, 106, 56), (2, 4, 12, 7))
        pygame.draw.rect(s, (186, 132, 76), (3, 5, 10, 3))
        pygame.draw.rect(s, (104, 64, 30), (2, 11, 12, 2))

    # 5. Книжный шкаф
    def draw_bookshelf(s):
        pygame.draw.rect(s, (22, 22, 30), (1, 0, 14, 16))
        pygame.draw.rect(s, (112, 68, 34), (2, 1, 12, 14))
        for sy in (5, 10):
            pygame.draw.line(s, (72, 42, 20), (2, sy), (13, sy), 1)
        book_cols = [(200, 60, 60), (65, 130, 200), (70, 165, 85), (225, 185, 60), (155, 80, 190)]
        for row_y in (2, 7, 12):
            for bx in range(3, 12, 2):
                pygame.draw.rect(s, random.choice(book_cols), (bx, row_y, 2, 3))

    # 6. Кровать (верх и низ)
    def draw_bed(s):
        pygame.draw.rect(s, (22, 22, 30), (2, 1, 12, 14))
        pygame.draw.rect(s, (120, 72, 36), (3, 2, 10, 3))    # Изголовье
        pygame.draw.rect(s, (235, 235, 240), (4, 5, 8, 3))   # Подушка
        pygame.draw.rect(s, (180, 55, 65), (3, 8, 10, 6))    # Одеяло

    # 7. Наковальня
    def draw_anvil(s):
        pygame.draw.rect(s, (22, 22, 30), (3, 5, 10, 9))
        pygame.draw.rect(s, (130, 140, 155), (2, 6, 12, 3))
        pygame.draw.rect(s, (95, 102, 115), (5, 9, 6, 3))
        pygame.draw.rect(s, (70, 75, 85), (3, 12, 10, 2))

    # 8. Горн / Камин с огнем
    def draw_forge(s):
        pygame.draw.rect(s, (22, 22, 30), (1, 1, 14, 14))
        pygame.draw.rect(s, (95, 100, 110), (2, 2, 12, 12))
        pygame.draw.rect(s, (30, 25, 25), (4, 6, 8, 7))
        pygame.draw.rect(s, (235, 90, 30), (5, 8, 6, 5))
        pygame.draw.rect(s, (250, 215, 70), (6, 9, 4, 3))

    # 9. Бочка
    def draw_barrel(s):
        pygame.draw.rect(s, (22, 22, 30), (3, 2, 10, 13))
        pygame.draw.rect(s, (145, 92, 44), (4, 3, 8, 11))
        pygame.draw.line(s, (75, 80, 90), (4, 5), (11, 5), 1)
        pygame.draw.line(s, (75, 80, 90), (4, 11), (11, 11), 1)

    _INTERIOR_SPRITES.update({
        "wood_floor": make_tile(draw_wood_floor),
        "stone_floor": make_tile(draw_stone_floor),
        "carpet": make_tile(draw_carpet),
        "table": make_tile(draw_table),
        "bookshelf": make_tile(draw_bookshelf),
        "bed": make_tile(draw_bed),
        "anvil": make_tile(draw_anvil),
        "forge": make_tile(draw_forge),
        "barrel": make_tile(draw_barrel),
    })
    return _INTERIOR_SPRITES


class InteriorRoom(WorldMap):
    """Внутренняя комната здания со своей мебелью, НПС и дверью выхода на улицу"""
    def __init__(self, building, cols, rows, return_pos):
        self.building = building
        self.return_pos = return_pos  # Координаты на улице перед дверью, куда вернется игрок
        self.exit_rect = None
        self.interactive_props = []   # Список (rect, kind, label) для кровати, наковальни, книжного шкафа
        super().__init__(cols=cols, rows=rows)
        self.buildings = []
        self.building_plots = []

    def build_town_square(self):
        # Переопределяем базовую генерацию площади, чтобы комната строилась чисто
        pass

    def draw(self, surface, sprites, camera, speech_font=None):
        merged_sprites = dict(sprites)
        merged_sprites.update(get_interior_sprites())
        super().draw(surface, merged_sprites, camera, speech_font)
def _spawn_interior_npc(name, tx, ty, role, faction, sprites, items_ids, greeting, teach_prof=None):
    app = generate_random_appearance("human")
    if role == "merchant":
        app["body"] = "robe"
    npc = Entity(name, tx * TILE_SIZE, ty * TILE_SIZE, (210, 175, 65),
                 sprite=build_character_sprite(app), faction=faction, sprite_bank=sprites)
    npc.appearance = app
    npc.stats = Stats(hp=80, mp=30, str_val=4, end_val=2)
    npc.inventory = Inventory(capacity=20, gold=500)
    for iid in items_ids:
        if iid in ITEMS_DB:
            npc.inventory.add_item(ITEMS_DB[iid])
    npc.ai = AIController(npc, role=role, aggro_radius=0)
    dlg = {"greeting": greeting}
    if teach_prof:
        dlg["teach_profession"] = teach_prof
    npc.dialogue = dlg
    npc.link_components()
    return npc


def generate_interior(building, sprites, return_pos):
    """
    Единая функция генерации интерьера под размер и назначение фасада building.
    Внутри комната всегда просторнее фасада снаружи.
    """
    meta = building.meta
    kind = building.kind
    size = meta.get("size", "medium")
    rng = random.Random(meta.get("seed") or hash(building.id))

    # Размеры комнаты внутри (всегда больше наружного фасада)
    size_map = {
        "small":  (12, 9),
        "medium": (16, 11),
        "large":  (20, 14),
        "hall":   (24, 16),
    }
    cols, rows = size_map.get(size, (16, 11))
    room = InteriorRoom(building, cols, rows, return_pos)

    floor_tile = "stone_floor" if kind == "smithy" else "wood_floor"
    for r in range(rows):
        for c in range(cols):
            room.tiles[r][c] = floor_tile

    # Стены по периметру комнаты
    for c in range(cols):
        room.tiles[0][c] = "wall"
        room.tiles[rows - 1][c] = "wall"
    for r in range(rows):
        room.tiles[r][0] = "wall"
        room.tiles[r][cols - 1] = "wall"

    # Дверь выхода внизу по центру + красный ковер у входа
    door_c = cols // 2
    room.tiles[rows - 1][door_c] = "carpet"
    room.tiles[rows - 2][door_c] = "carpet"
    room.exit_rect = pygame.Rect(door_c * TILE_SIZE - 4, (rows - 1) * TILE_SIZE - 6, TILE_SIZE + 8, TILE_SIZE + 8)

    def place_prop(c, r, tile_name, solid=True, interact_kind=None, label=""):
        if 1 <= r < rows - 1 and 1 <= c < cols - 1:
            room.tiles[r][c] = tile_name
            rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if solid:
                room.walls.append(rect)
            if interact_kind:
                room.interactive_props.append((rect.inflate(10, 10), interact_kind, label))

    # Собираем базовые стены
    room.walls = [
        pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        for r in range(rows) for c in range(cols)
        if room.tiles[r][c] == "wall"
    ]

    # --- НАПОЛНЕНИЕ ПО ТИПУ ЗДАНИЯ ---
    if kind == "tavern":
        # Камин, бочки, барная стойка и столы для гостей
        place_prop(2, 1, "forge", solid=True)
        place_prop(cols - 3, 1, "barrel", solid=True)
        place_prop(cols - 2, 1, "barrel", solid=True)
        bar_c1, bar_c2 = max(3, door_c - 3), min(cols - 4, door_c + 3)
        for c in range(bar_c1, bar_c2 + 1):
            place_prop(c, 3, "table", solid=True)
        # Столы в зале (для больших таверн — два ряда)
        for tr in range(5, rows - 3, 3):
            place_prop(3, tr, "table", solid=True)
            place_prop(cols - 4, tr, "table", solid=True)

        innkeeper = _spawn_interior_npc(
            "Трактирщик Боб", door_c, 2, "merchant", "town", sprites,
            ["potion", "potion", "mana_potion", "speed_potion", "antidote"],
            "Добро пожаловать в нашу таверну! У нас лучшая похлебка и зелья в округе."
        )
        room.entities.append(innkeeper)

    elif kind == "smithy":
        # Горн, наковальня (интерактивный верстак!), бочки с водой и сундук с рудой
        place_prop(3, 1, "forge", solid=True)
        place_prop(4, 1, "forge", solid=True)
        place_prop(4, 3, "anvil", solid=True, interact_kind="workbench", label="Наковальня [E — Ковать]")
        place_prop(2, 3, "barrel", solid=True)
        for c in range(cols - 5, cols - 2):
            place_prop(c, 3, "table", solid=True)

        smith = _spawn_interior_npc(
            "Кузнец Торин", cols - 4, 2, "merchant", "town", sprites,
            ["iron_sword", "chainmail", "leather_armor", "iron_ore", "wood_log"],
            "Жар горна закаляет лучшую сталь! Можешь воспользоваться моей наковальней.",
            teach_prof={"id": "blacksmith", "cost": 40, "text": "Я научил тебя кузнечному делу! Нажми [P] или подойди к наковальне."}
        )
        room.entities.append(smith)

    elif kind == "shop":
        # Книжные шкафы, прилавок и сундук с товарами
        for c in range(2, cols - 2, 2):
            place_prop(c, 1, "bookshelf", solid=True)
        for c in range(max(3, door_c - 2), min(cols - 3, door_c + 3)):
            place_prop(c, 3, "table", solid=True)
        place_prop(2, rows - 3, "barrel", solid=True)

        trader = _spawn_interior_npc(
            "Лавочник Марк", door_c, 2, "merchant", "town", sprites,
            ["potion", "mana_potion", "hunting_bow", "power_ring", "big_bag", "herb_leaf", "leather_piece"],
            "Заходи, выбирай! Все товары по честной цене."
        )
        room.entities.append(trader)

    elif kind == "guild":
        # Библиотека, длинный стол совета и наставник
        for c in range(2, cols - 2):
            place_prop(c, 1, "bookshelf", solid=True)
        for c in range(4, cols - 4):
            place_prop(c, rows // 2, "table", solid=True)
        master = _spawn_interior_npc(
            "Магистр Гильдии", door_c, 2, "merchant", "town", sprites,
            ["fire_staff", "mage_ring", "book_fire", "book_heal", "scroll_mind_expand"],
            "Знание — главная сила искателя приключений."
        )
        room.entities.append(master)

    else:
        # Уютный жилой дом: кровать для отдыха, книжный шкаф, стол и сундук хозяина
        place_prop(2, 1, "bed", solid=True, interact_kind="bed", label="Кровать [E — Отдохнуть]")
        place_prop(cols - 3, 1, "bookshelf", solid=True)
        place_prop(cols // 2, 3, "table", solid=True)

        chest = Entity("Домашний сундук", (cols - 3) * TILE_SIZE, (rows - 3) * TILE_SIZE, (180, 120, 60),
                       sprite=sprites.get("chest"), is_container=True)
        chest.inventory = Inventory(capacity=8, gold=rng.randint(15, 60))
        if "potion" in ITEMS_DB:
            chest.inventory.add_item(ITEMS_DB["potion"])
        room.entities.append(chest)

        citizen = _spawn_interior_npc(
            "Горожанин", 4, 4, "adventurer", "town", sprites, [],
            "Привет! Не стесняйся, можешь передохнуть у меня дома."
        )
        room.entities.append(citizen)

    # Координаты появления игрока внутри у входной двери
    room.spawn_pos = (door_c * TILE_SIZE, (rows - 2) * TILE_SIZE)
    return room
