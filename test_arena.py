import pygame
import sys
import math
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, NATIVE_WIDTH, NATIVE_HEIGHT, SCALE, FPS, TILE_SIZE
from database import DatabaseManager
from sprites import load_sprites
from world import WorldMap, Camera
from ui import UIManager
from hud import draw_hud
from entities import Entity
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.skills import SkillBook
from components.quests import QuestLog
from components.ai import AIController
from items import ITEMS_DB
from appearance import build_character_sprite, generate_random_appearance
from monster_gen import generate_monster


def build_showcase_map(world):
    """Создает красивый разделенный на зоны полигон: площадь, торговый ряд, озеро и арену"""
    for r in range(world.rows):
        for c in range(world.cols):
            world.tiles[r][c] = "grass"

    # 1. Центральная площадь из брусчатки (c: 12..26, r: 7..18)
    for r in range(7, 19):
        for c in range(12, 27):
            world.tiles[r][c] = "cobble"

    # 2. Декоративное озеро с песчаным пляжем на юге площади (cx=19, cy=21)
    for r in range(world.rows):
        for c in range(world.cols):
            dist = math.hypot((c - 19) * 0.75, (r - 21) * 1.1)
            if dist < 2.3:
                world.tiles[r][c] = "water"
            elif dist < 3.4 and world.tiles[r][c] == "grass":
                world.tiles[r][c] = "sand"

    # 3. Западный торговый двор (c: 3..10, r: 5..20) и дорожка к нему
    for r in range(5, 21):
        for c in range(3, 11):
            world.tiles[r][c] = "dirt"
    for r in range(11, 14):
        for c in range(11, 13):
            world.tiles[r][c] = "cobble"

    # 4. Восточная боевая арена (c: 29..39, r: 4..21) и ворота к ней
    for r in range(4, 22):
        for c in range(29, 40):
            world.tiles[r][c] = "sand" if (r + c) % 5 == 0 else "dirt"

    # Стена-разделитель с широкими воротами на арену (c = 28)
    for r in range(1, world.rows - 1):
        if r not in (11, 12, 13):
            world.tiles[r][28] = "wall"
    for c in range(27, 30):
        for r in (11, 12, 13):
            world.tiles[r][c] = "cobble"

    # Внешние каменные стены по периметру
    for c in range(world.cols):
        world.tiles[0][c] = "wall"
        world.tiles[world.rows - 1][c] = "wall"
    for r in range(world.rows):
        world.tiles[r][0] = "wall"
        world.tiles[r][world.cols - 1] = "wall"

    world.building_plots = [
        pygame.Rect(4 * TILE_SIZE, 6 * TILE_SIZE, 5 * TILE_SIZE, 3 * TILE_SIZE),
    ]
    world.walls = [
        pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        for r in range(world.rows) for c in range(world.cols)
        if world.tiles[r][c] in ("wall", "water")
    ]


def create_showcase_player(sprites):
    app = {"body": "heavy_tunic", "head": "human", "hair": "short", "skin": 0, "hair_color": 1, "eye_color": 1, "cloth_color": 0}
    p = Entity("Тестер-Герой", 18 * TILE_SIZE, 12 * TILE_SIZE, (70, 140, 220), sprite=build_character_sprite(app), faction="player", sprite_bank=sprites)
    p.appearance = app
    p.movement = Movement(p, speed=95)
    p.inventory = Inventory(capacity=24, gold=2500)
    p.equipment = Equipment()
    p.stats = Stats(hp=120, mp=100, str_val=8, agi_val=8, int_val=8, vit_val=6, end_val=4)
    p.combat = Combat(p, cooldown=0.35)
    p.skills = SkillBook(p, max_slots=8, max_active_slots=3)
    p.quests = QuestLog(p)
    p.link_components()

    # Выдаем стартовый набор для быстрого теста всех механик
    starter_ids = ["iron_sword", "hunting_bow", "fire_staff", "chainmail", "potion", "potion", "mana_potion", "speed_potion", "scroll_mind_expand"]
    for iid in starter_ids:
        if iid in ITEMS_DB:
            p.inventory.add_item(ITEMS_DB[iid])

    p.equipment.equip(ITEMS_DB["iron_sword"], p.inventory)
    p.equipment.equip(ITEMS_DB["chainmail"], p.inventory)
    p.quick_items = ["potion", "mana_potion", "speed_potion", "scroll_mind_expand"]

    for sk_id in ("whirlwind", "volley", "ice_bolt", "passive_blade"):
        p.skills.learn_skill(sk_id)

    return p


def populate_showcase_world(world, player, sprites, db):
    world.entities = [player]

    # 1. НЕПОДВИЖНЫЙ ТОРГОВЕЦ ВСЕМИ ПРЕДМЕТАМИ (Западный ряд, верх)
    all_items = list(ITEMS_DB.values())
    merch_app = {"body": "robe", "head": "elf", "hair": "long", "skin": 0, "hair_color": 4, "eye_color": 4, "cloth_color": 6}
    merchant = Entity("Архивариус (Все товары)", 6 * TILE_SIZE, 10 * TILE_SIZE, (230, 190, 65),
                      sprite=build_character_sprite(merch_app), faction="free_city", sprite_bank=sprites)
    merchant.appearance = merch_app
    merchant.stats = Stats(hp=999, mp=100, str_val=5, end_val=10)
    merchant.inventory = Inventory(capacity=len(all_items) + 10, gold=50000)
    for it in all_items:
        merchant.inventory.add_item(it)
    merchant.ai = AIController(merchant, role="merchant", aggro_radius=0)
    merchant.dialogue = {
        "greeting": "Добро пожаловать на полигон! У меня в наличии ВСЕ предметы, книги и ресурсы игры.",
        "rumor": "На востоке за воротами ждут монстры всех видов, а у сундуков лежат ресурсы для крафта [P]."
    }
    merchant.link_components()
    world.entities.append(merchant)

    # 2. НЕПОДВИЖНЫЙ НАСТАВНИК ПРОФЕССИЙ (Западный ряд, центр)
    mentor_app = {"body": "heavy_tunic", "head": "human", "hair": "bald", "skin": 1, "hair_color": 2, "eye_color": 2, "cloth_color": 1}
    mentor = Entity("Грандмастер Ремесел", 6 * TILE_SIZE, 13 * TILE_SIZE, (120, 220, 150),
                    sprite=build_character_sprite(mentor_app), faction="free_city", sprite_bank=sprites)
    mentor.appearance = mentor_app
    mentor.stats = Stats(hp=999, mp=100, str_val=5, end_val=10)
    mentor.ai = AIController(mentor, role="merchant", aggro_radius=0)
    mentor.dialogue = {
        "greeting": "Я могу обучить тебя любой профессии! Нажми [P], чтобы открыть верстак.",
        "rumor": "В сундуках рядом лежат руда, дерево, кожа и травы для проверки всех рецептов.",
        "teach_profession": {"id": "blacksmith", "cost": 0, "text": "Ты освоил кузнечное дело!"}
    }
    mentor.link_components()
    world.entities.append(mentor)

    # 3. ТРИ ТЕСТОВЫХ СУНДУКА С МАТЕРИАЛАМИ И СНАРЯЖЕНИЕМ
    chests_cfg = [
        ("Сундук Кузнеца", 4 * TILE_SIZE, 16 * TILE_SIZE, ["iron_ore", "iron_ore", "iron_ore", "wood_log", "wood_log", "leather_piece"]),
        ("Сундук Алхимика", 6 * TILE_SIZE, 16 * TILE_SIZE, ["herb_leaf", "herb_leaf", "herb_leaf", "herb_leaf", "wood_log", "antidote"]),
        ("Сундук Сокровищ", 8 * TILE_SIZE, 16 * TILE_SIZE, ["gem", "gem", "power_ring", "mage_ring", "guard_amulet", "big_bag"]),
    ]
    for cname, cx, cy, citems in chests_cfg:
        ch = Entity(cname, cx, cy, (180, 120, 60), sprite=sprites.get("chest"), is_container=True)
        ch.inventory = Inventory(capacity=16, gold=500)
        for iid in citems:
            if iid in ITEMS_DB:
                ch.inventory.add_item(ITEMS_DB[iid])
        world.entities.append(ch)

    # 4. СОЮЗНЫЙ СТРАЖНИК У ВОРОТ НА АРЕНУ
    guard_app = {"body": "heavy_tunic", "head": "human", "hair": "short", "skin": 0, "hair_color": 0, "eye_color": 0, "cloth_color": 2}
    guard = Entity("Страж Арены", 25 * TILE_SIZE, 10 * TILE_SIZE, (190, 60, 60),
                   sprite=build_character_sprite(guard_app), faction="town", sprite_bank=sprites)
    guard.appearance = guard_app
    guard.movement = Movement(guard, speed=55)
    guard.stats = Stats(hp=120, mp=30, str_val=8, vit_val=4, end_val=3)
    guard.inventory = Inventory(capacity=6, gold=50)
    guard.equipment = Equipment()
    if "iron_sword" in ITEMS_DB:
        guard.inventory.add_item(ITEMS_DB["iron_sword"])
        guard.equipment.equip(ITEMS_DB["iron_sword"], guard.inventory)
    guard.combat = Combat(guard, cooldown=0.5)
    guard.ai = AIController(guard, role="guard", aggro_radius=120)
    guard.link_components()
    world.entities.append(guard)

    # 5. ПО ОДНОМУ МОНСТРУ КАЖДОГО АРХЕТИПА ИЗ БД НА ВОСТОЧНОЙ АРЕНЕ
    cur = db.conn.cursor()
    cur.execute("SELECT id FROM monster_archetypes")
    arch_ids = [r["id"] for r in cur.fetchall()]
    for idx in range(5):
        mx = (33 + (idx % 3) * 2) * TILE_SIZE
        my = (6 + idx * 3) * TILE_SIZE
        mob = generate_monster(mx, my, sprites, db=db)
        world.entities.append(mob)

def run_test_arena():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    native_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
    pygame.display.set_caption("8-Bit RPG — ТЕСТОВЫЙ ПОЛИГОН (Все механики)")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("consolas", 17, bold=True)
    speech_font = pygame.font.SysFont("consolas", 15, bold=True)

    db = DatabaseManager("rpg.db")
    db.sync_all_catalogs()
    sprites = load_sprites(db)

    world = WorldMap(cols=42, rows=26)
    build_showcase_map(world)

    player = create_showcase_player(sprites)
    populate_showcase_world(world, player, sprites, db)

    camera = Camera(world.width, world.height)
    ui = UIManager(player, world.entities, sprites.get("loot"), sprites)

    status_msg = "ПОЛИГОН | F1: Полный хил | F2: +1000G и Уровень | F3: Спавн врагов | I/P/K/C: Окна"

    while True:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if ui.is_open:
                msg = ui.handle_input(event)
                if msg:
                    status_msg = msg
                continue

            if ui.handle_global_hotkey(event):
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_F1:
                    player.stats.hp = float(player.stats.max_hp)
                    player.stats.mp = float(player.stats.max_mp)
                    if player.effects:
                        player.effects.active.clear()
                    if player.skills:
                        for sk in player.skills.learned:
                            sk.timer = 0.0
                    status_msg = "F1: HP, MP и откаты навыков полностью восстановлены!"
                elif event.key == pygame.K_F2:
                    player.inventory.gold += 1000
                    player.stats.gain_xp(player.stats.xp_to_next)
                    status_msg = f"F2: +1000G! Уровень героя: {player.stats.level} (Очков статов: {player.stats.stat_points})"
                elif event.key == pygame.K_F3:
                    mob = generate_monster(35 * TILE_SIZE, 12 * TILE_SIZE, sprites, db=db)
                    world.entities.append(mob)
                    status_msg = f"F3: На арене появился {mob.name}!"
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6) and player.skills:
                    slot_idx = event.key - pygame.K_1
                    mx, my = pygame.mouse.get_pos()
                    aim = (mx // SCALE + camera.offset_x, my // SCALE + camera.offset_y)
                    _, msg = player.skills.use_active_slot(slot_idx, world, aim_pos=aim)
                    if msg:
                        status_msg = msg
                elif event.key in (pygame.K_q, pygame.K_f, pygame.K_z, pygame.K_x):
                    q_map = {pygame.K_q: 0, pygame.K_f: 1, pygame.K_z: 2, pygame.K_x: 3}
                    msg = player.use_quick_item(q_map[event.key])
                    if msg:
                        status_msg = msg
                elif event.key == pygame.K_SPACE and player.combat:
                    mx, my = pygame.mouse.get_pos()
                    aim = (mx // SCALE + camera.offset_x, my // SCALE + camera.offset_y)
                    player.combat.attack(world, aim_pos=aim)
                elif event.key == pygame.K_e:
                    for ent in world.entities:
                        if ent is not player and player.rect.inflate(18, 18).colliderect(ent.rect):
                            # На полигоне Наставник обучает всем еще не изученным профессиям бесплатно!
                            if ent.name == "Грандмастер Ремесел" and player.professions:
                                from components.professions import PROFESSIONS_DB
                                for pid in PROFESSIONS_DB:
                                    player.professions.learn(pid, level=1)
                            msg = ent.interact(player, ui)
                            if msg:
                                status_msg = msg
                                break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and player.combat:
                mx, my = event.pos
                aim = (mx // SCALE + camera.offset_x, my // SCALE + camera.offset_y)
                player.combat.attack(world, aim_pos=aim)

        if not ui.is_open:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if player.movement:
                player.movement.move(dx, dy, dt, world.walls)

            world_msg = world.update(dt, player, ui, sprites.get("loot"))
            if world_msg:
                status_msg = world_msg

            if player.stats.hp <= 0:
                status_msg = "ГЕРОЙ ПАЛ НА ПОЛИГОНЕ! Нажмите R для мгновенного возрождения."
                if keys[pygame.K_r]:
                    player.stats.hp = float(player.stats.max_hp)
                    player.stats.mp = float(player.stats.max_mp)
                    player.rect.topleft = (18 * TILE_SIZE, 12 * TILE_SIZE)
                    player.movement.pos_x, player.movement.pos_y = float(player.rect.x), float(player.rect.y)
                    status_msg = "Герой возрожден в центре полигона!"

        native_surface.fill((15, 18, 24))
        camera.follow(player)
        if not ui.is_open and player.stats.hp > 0:
            mx, my = pygame.mouse.get_pos()
            player.facing_left = ((mx // SCALE + camera.offset_x) < player.rect.centerx)

        world.draw(native_surface, sprites, camera, None)

        screen.blit(pygame.transform.scale(native_surface, (WINDOW_WIDTH, WINDOW_HEIGHT)), (0, 0))
        world.draw_speeches(screen, camera, SCALE, speech_font)
        if not ui.is_open:
            draw_hud(screen, player, status_msg, hud_font, sprites)
        ui.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    run_test_arena()
