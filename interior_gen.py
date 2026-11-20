import pygame
import random
import json
from settings import TILE_SIZE
from world import WorldMap
from entities import Entity
from components.inventory import Inventory
from components.stats import Stats
from components.ai import AIController
from items import ITEMS_DB
from appearance import build_character_sprite, generate_random_appearance
from furniture import get_furniture_sprite

_FLOOR_SPRITES = {}

def get_floor_sprites():
    if _FLOOR_SPRITES:
        return _FLOOR_SPRITES

    def make_tile(fn):
        s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        fn(s)
        return s

    def draw_wood(s):
        s.fill((128, 84, 46))
        for y in (0, 8):
            pygame.draw.line(s, (92, 56, 28), (0, y), (15, y), 1)
            pygame.draw.line(s, (148, 102, 58), (0, y + 1), (15, y + 1), 1)
        pygame.draw.line(s, (92, 56, 28), (7, 0), (7, 7), 1)
        pygame.draw.line(s, (92, 56, 28), (13, 8), (13, 15), 1)

    def draw_stone(s):
        s.fill((105, 110, 120))
        pygame.draw.rect(s, (122, 128, 140), (1, 1, 6, 6))
        pygame.draw.rect(s, (122, 128, 140), (9, 9, 6, 6))
        pygame.draw.line(s, (75, 80, 90), (0, 8), (15, 8), 1)
        pygame.draw.line(s, (75, 80, 90), (8, 0), (8, 15), 1)

    def draw_carpet(s):
        s.fill((165, 48, 48))
        pygame.draw.rect(s, (225, 180, 65), (1, 1, 14, 14), 1)

    _FLOOR_SPRITES.update({
        "wood_floor": make_tile(draw_wood),
        "stone_floor": make_tile(draw_stone),
        "carpet": make_tile(draw_carpet),
    })
    return _FLOOR_SPRITES


class InteriorRoom(WorldMap):
    def __init__(self, building, cols, rows, return_pos):
        self.building = building
        self.return_pos = return_pos
        self.exit_rect = None
        self.props_list = []          # [{'c': int, 'r': int, 'id': str, 'solid': bool, 'interact_kind': str|None, 'label': str}]
        self.interactive_props = []
        super().__init__(cols=cols, rows=rows)
        self.buildings = []
        self.building_plots = []

    def build_town_square(self):
        pass

    def draw(self, surface, sprites, camera, speech_font=None):
        merged = dict(sprites)
        merged.update(get_floor_sprites())

        # 1. Рисуем цельный пол и стены
        start_c = max(0, camera.offset_x // TILE_SIZE)
        end_c = min(self.cols, (camera.offset_x + 320) // TILE_SIZE + 2)
        start_r = max(0, camera.offset_y // TILE_SIZE)
        end_r = min(self.rows, (camera.offset_y + 180) // TILE_SIZE + 2)

        for r in range(start_r, end_r):
            for c in range(start_c, end_c):
                spr = merged.get(self.tiles[r][c], merged.get("stone_floor"))
                if spr:
                    surface.blit(spr, (c * TILE_SIZE - camera.offset_x, r * TILE_SIZE - camera.offset_y))

        # 2. Собираем множество координат столов для бесшовной склейки прилавков
        table_coords = {(p["c"], p["r"]) for p in self.props_list if p["id"] == "table"}

        # 3. Сортируем мебель и персонажей по нижней грани (Y-сортировка глубины)
        renderables = []
        for p in self.props_list:
            px, py = p["c"] * TILE_SIZE, p["r"] * TILE_SIZE
            custom_key = p.get("sprite_key")
            if custom_key and custom_key in merged:
                spr = merged[custom_key]
            else:
                conn_l = (p["id"] == "table" and (p["c"] - 1, p["r"]) in table_coords)
                conn_r = (p["id"] == "table" and (p["c"] + 1, p["r"]) in table_coords)
                spr = get_furniture_sprite(p["id"], conn_l, conn_r)
            renderables.append((py + TILE_SIZE, "prop", (spr, px, py)))


        for ent in self.entities:
            renderables.append((ent.rect.bottom, "entity", ent))

        renderables.sort(key=lambda item: item[0])

        for _, r_type, obj in renderables:
            if r_type == "prop":
                spr, px, py = obj
                surface.blit(spr, (px - camera.offset_x, py - camera.offset_y))
            else:
                orig_pos = obj.rect.topleft
                obj.rect.x -= camera.offset_x
                obj.rect.y -= camera.offset_y
                if obj.combat and obj.combat.swing_rect:
                    obj.combat.swing_rect.x -= camera.offset_x
                    obj.combat.swing_rect.y -= camera.offset_y
                obj.draw(surface, None)
                obj.rect.topleft = orig_pos
                if obj.combat and obj.combat.swing_rect:
                    obj.combat.swing_rect.x += camera.offset_x
                    obj.combat.swing_rect.y += camera.offset_y


def _spawn_npc_from_cfg(cfg, sprites):
    app = cfg.get("appearance") or generate_random_appearance("human")
    npc = Entity(cfg["name"], cfg["c"] * TILE_SIZE, cfg["r"] * TILE_SIZE, (210, 175, 65),
                 sprite=build_character_sprite(app), faction="town", sprite_bank=sprites)
    npc.appearance = app
    npc.stats = Stats(hp=80, mp=30, str_val=4, end_val=2)
    npc.inventory = Inventory(capacity=20, gold=500)
    for iid in cfg.get("items", []):
        if iid in ITEMS_DB:
            npc.inventory.add_item(ITEMS_DB[iid])
    npc.ai = AIController(npc, role=cfg.get("role", "merchant"), aggro_radius=0)
    dlg = {"greeting": cfg.get("greeting", "Приветствую!")}
    if cfg.get("teach_prof"):
        dlg["teach_profession"] = cfg["teach_prof"]
    npc.dialogue = dlg
    npc.link_components()
    return npc


def generate_interior(building, sprites, return_pos, db=None):
    """Загружает интерьер здания из БД или генерирует и сохраняет в БД"""
    meta = building.meta
    kind = building.kind
    size = meta.get("size", "medium")
    rng = random.Random(meta.get("seed") or hash(building.id))

    saved = db.get_building_interior(building.id) if db else None
    if saved:
        cols, rows = saved["cols"], saved["rows"]
        floor_tile = saved["floor_tile"]
        props_list = json.loads(saved["props_json"])
        npcs_list = json.loads(saved["npcs_json"])
    else:
        size_map = {"small": (12, 9), "medium": (16, 11), "large": (20, 14), "hall": (24, 16)}
        cols, rows = size_map.get(size, (16, 11))
        floor_tile = "stone_floor" if kind == "smithy" else "wood_floor"
        door_c = cols // 2
        props_list = []
        npcs_list = []

        def add_prop(c, r, pid, solid=True, ikind=None, lbl=""):
            if 1 <= r < rows - 1 and 1 <= c < cols - 1:
                spr_k = None
                if db:
                    cur = db.conn.cursor()
                    cur.execute("SELECT sprite_key FROM furniture_catalog WHERE id = ?", (pid,))
                    f_row = cur.fetchone()
                    if f_row and f_row["sprite_key"]:
                        spr_k = f_row["sprite_key"]
                props_list.append({
                    "c": c, "r": r, "id": pid, "solid": solid,
                    "interact_kind": ikind, "label": lbl, "sprite_key": spr_k
                })

        if kind == "tavern":
            add_prop(2, 1, "forge", True)
            add_prop(cols - 3, 1, "barrel", True)
            add_prop(cols - 2, 1, "barrel", True)
            for c in range(max(3, door_c - 3), min(cols - 3, door_c + 4)):
                add_prop(c, 3, "table", True)
            for tr in range(5, rows - 3, 3):
                add_prop(3, tr, "table", True)
                add_prop(4, tr, "table", True)
                add_prop(3, tr + 1, "chair", False)
                add_prop(cols - 5, tr, "table", True)
                add_prop(cols - 4, tr, "table", True)
                add_prop(cols - 4, tr + 1, "chair", False)
            npcs_list.append({
                "name": "Трактирщик Боб", "c": door_c, "r": 2, "role": "merchant",
                "items": ["potion", "potion", "mana_potion", "speed_potion", "antidote"],
                "greeting": "Добро пожаловать в нашу таверну! У нас лучшая похлебка и зелья.",
                "appearance": generate_random_appearance("human")
            })

        elif kind == "smithy":
            add_prop(3, 1, "forge", True)
            add_prop(4, 1, "forge", True)
            add_prop(4, 3, "anvil", True, "workbench", "Наковальня [E — Ковать]")
            add_prop(2, 3, "barrel", True)
            add_prop(cols - 3, 1, "weapon_rack", True)
            for c in range(cols - 5, cols - 2):
                add_prop(c, 3, "table", True)
            npcs_list.append({
                "name": "Кузнец Торин", "c": cols - 4, "r": 2, "role": "merchant",
                "items": ["iron_sword", "chainmail", "leather_armor", "iron_ore", "wood_log"],
                "greeting": "Жар горна закаляет лучшую сталь! Можешь воспользоваться моей наковальней.",
                "teach_prof": {"id": "blacksmith", "cost": 40, "text": "Я научил тебя кузнечному делу!"},
                "appearance": generate_random_appearance("human")
            })

        elif kind == "shop":
            for c in range(2, cols - 2, 2):
                add_prop(c, 1, "bookshelf", True)
            for c in range(max(3, door_c - 2), min(cols - 3, door_c + 3)):
                add_prop(c, 3, "table", True)
            add_prop(2, rows - 3, "barrel", True)
            add_prop(cols - 3, rows - 3, "plant", True)
            npcs_list.append({
                "name": "Лавочник Марк", "c": door_c, "r": 2, "role": "merchant",
                "items": ["potion", "mana_potion", "hunting_bow", "power_ring", "big_bag", "herb_leaf", "leather_piece"],
                "greeting": "Заходи, выбирай! Все товары по честной цене.",
                "appearance": generate_random_appearance("human")
            })

        else:
            add_prop(2, 1, "bed", True, "bed", "Кровать [E — Отдохнуть]")
            add_prop(cols - 3, 1, "bookshelf", True)
            add_prop(cols // 2, 3, "table", True)
            add_prop(cols // 2 + 1, 3, "table", True)
            add_prop(cols // 2, 4, "chair", False)
            add_prop(2, rows - 3, "plant", True)
            npcs_list.append({
                "name": "Горожанин", "c": 4, "r": 4, "role": "adventurer", "items": [],
                "greeting": "Привет! Не стесняйся, можешь передохнуть на моей кровати.",
                "appearance": generate_random_appearance("human")
            })

        if db:
            db.save_building_interior(building.id, kind, cols, rows, floor_tile, props_list, npcs_list)

    # Собираем комнату
    room = InteriorRoom(building, cols, rows, return_pos)
    for r in range(rows):
        for c in range(cols):
            room.tiles[r][c] = floor_tile

    for c in range(cols):
        room.tiles[0][c] = "wall"
        room.tiles[rows - 1][c] = "wall"
    for r in range(rows):
        room.tiles[r][0] = "wall"
        room.tiles[r][cols - 1] = "wall"

    door_c = cols // 2
    room.tiles[rows - 1][door_c] = "carpet"
    room.tiles[rows - 2][door_c] = "carpet"
    room.exit_rect = pygame.Rect(door_c * TILE_SIZE - 4, (rows - 1) * TILE_SIZE - 6, TILE_SIZE + 8, TILE_SIZE + 8)

    room.walls = [
        pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        for r in range(rows) for c in range(cols)
        if room.tiles[r][c] == "wall"
    ]

    room.props_list = props_list
    # Подтягиваем актуальные спрайты мебели из каталога БД (если их изменили в editor.py)
    if db:
        cur = db.conn.cursor()
        cur.execute("SELECT id, sprite_key FROM furniture_catalog")
        fresh_sprites = {r["id"]: r["sprite_key"] for r in cur.fetchall()}
        for p in props_list:
            if p["id"] in fresh_sprites and fresh_sprites[p["id"]]:
                p["sprite_key"] = fresh_sprites[p["id"]]

    for p in props_list:
        rect = pygame.Rect(p["c"] * TILE_SIZE, p["r"] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if p.get("solid", True):
            room.walls.append(rect)
        if p.get("interact_kind"):
            room.interactive_props.append((rect.inflate(10, 10), p["interact_kind"], p.get("label", "")))

    for n_cfg in npcs_list:
        room.entities.append(_spawn_npc_from_cfg(n_cfg, sprites))

    room.spawn_pos = (door_c * TILE_SIZE, (rows - 2) * TILE_SIZE)
    return room
