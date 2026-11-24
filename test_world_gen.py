"""Тест генератора мира: биомы, реки, озёра, города, дома, подземелья.

Запуск:  python test_world_gen.py

Управление:
  WASD/стрелки — движение, Мышь/Space — атака, E — действие (двери, пещеры,
  сундуки, NPC), 1-6 — навыки, Q/F/Z/X — быстрые предметы,
  F1 — полный хил, F2 — +1000G и уровень, F3 — монстр рядом,
  F4 — перегенерировать мир (новый сид), M — миникарта,
  I/P/K/C — окна, ESC — выход.
"""
import math
import random
import sys

import pygame

from settings import WINDOW_WIDTH, WINDOW_HEIGHT, NATIVE_WIDTH, NATIVE_HEIGHT, SCALE, FPS, TILE_SIZE
from database import DatabaseManager
from sprites import load_sprites
from world import Camera
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
from appearance import build_character_sprite
from monster_gen import generate_monster
from building_gen import generate_building
from interior_gen import generate_interior
from world_gen import (generate_world, ensure_world_sprites, populate_world,
                       generate_dungeon, generate_city, BIOME_NAMES_RU)


def create_player(sprites):
    app = {"body": "heavy_tunic", "head": "human", "hair": "short", "skin": 0,
           "hair_color": 1, "eye_color": 1, "cloth_color": 0}
    p = Entity("Следопыт", 0, 0, (70, 140, 220),
               sprite=build_character_sprite(app), faction="player",
               sprite_bank=sprites)
    p.appearance = app
    p.movement = Movement(p, speed=100)
    p.inventory = Inventory(capacity=24, gold=500)
    p.equipment = Equipment()
    p.stats = Stats(hp=120, mp=100, str_val=8, agi_val=8, int_val=8,
                    vit_val=6, end_val=4)
    p.combat = Combat(p, cooldown=0.35)
    p.skills = SkillBook(p, max_slots=8, max_active_slots=3)
    p.quests = QuestLog(p)
    p.link_components()
    for iid in ("iron_sword", "potion", "potion", "mana_potion"):
        if iid in ITEMS_DB:
            p.inventory.add_item(ITEMS_DB[iid])
    if "iron_sword" in ITEMS_DB:
        p.equipment.equip(ITEMS_DB["iron_sword"], p.inventory)
    p.quick_items = ["potion", "potion", "mana_potion", None]
    for sk_id in ("whirlwind", "ice_bolt", "passive_blade"):
        p.skills.learn_skill(sk_id)
    return p


def make_world(sprites, db, player, seed=None):
    """Генерирует мир и заселяет его; возвращает (world, seed)."""
    if seed is None:
        seed = random.randint(0, 2 ** 31 - 1)
    world = generate_world(cols=112, rows=68, seed=seed)
    world.entities = populate_world(world, player, sprites, db)
    return world, seed


def draw_minimap(screen, world, player):
    mm = getattr(world, "minimap_surface", None)
    if mm is None:
        return
    scaled = pygame.transform.scale(mm, (mm.get_width() * 2, mm.get_height() * 2))
    x = WINDOW_WIDTH - scaled.get_width() - 8
    y = 8
    panel = pygame.Surface((scaled.get_width() + 4, scaled.get_height() + 4),
                           pygame.SRCALPHA)
    panel.fill((10, 12, 18, 200))
    screen.blit(panel, (x - 2, y - 2))
    screen.blit(scaled, (x, y))
    # Точка игрока
    pc = player.rect.centerx // TILE_SIZE
    pr = player.rect.centery // TILE_SIZE
    pygame.draw.rect(screen, (255, 255, 255),
                     (x + pc * 2 - 1, y + pr * 2 - 1, 3, 3))


def run_test_world_gen():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    native_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
    pygame.display.set_caption("8-Bit RPG — ГЕНЕРАТОР МИРА")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("consolas", 17, bold=True)
    speech_font = pygame.font.SysFont("consolas", 15, bold=True)

    db = DatabaseManager("rpg.db")
    db.sync_all_catalogs()
    sprites = load_sprites(db)
    ensure_world_sprites(sprites)

    player = create_player(sprites)
    world, world_seed = make_world(sprites, db, player)

    camera = Camera(world.width, world.height)
    ui = UIManager(player, world.entities, sprites.get("loot"), sprites)

    status_msg = (f"Мир.seed={world_seed} | F4: Новый мир | M: Карта | "
                  "E: Действие | WASD: движок")
    outdoor_world = world
    loc_stack = []           # стек родительских локаций (для возврата [E])
    interiors_cache = {}
    dungeons_cache = {}
    cities_cache = {}
    show_map = True
    home_pos = world.spawn_pos

    def enter_map(new_world, msg):
        """Уходит в под-локацию: запоминает текущую карту и позицию игрока."""
        nonlocal world, camera
        return_pos = player.rect.topleft
        loc_stack.append(world)
        world = new_world
        # Куда вернуться — перезаписываем при каждом входе
        world.return_pos = return_pos
        if player not in world.entities:
            world.entities.insert(0, player)
        camera = Camera(world.width, world.height)
        return msg

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

                elif event.key == pygame.K_m:
                    show_map = not show_map
                    status_msg = f"Миникарта: {'ВКЛ' if show_map else 'ВЫКЛ'}"

                elif event.key == pygame.K_F1:
                    player.stats.hp = float(player.stats.max_hp)
                    player.stats.mp = float(player.stats.max_mp)
                    if player.effects:
                        player.effects.active.clear()
                    status_msg = "F1: HP и MP полностью восстановлены!"
                elif event.key == pygame.K_F2:
                    player.inventory.gold += 1000
                    player.stats.gain_xp(player.stats.xp_to_next)
                    status_msg = (f"F2: +1000G! Уровень {player.stats.level}")
                elif event.key == pygame.K_F3:
                    tx = (player.rect.centerx // TILE_SIZE +
                          random.randint(-3, 3))
                    ty = (player.rect.centery // TILE_SIZE +
                          random.randint(-2, 2))
                    tx = max(1, min(world.cols - 2, tx))
                    ty = max(1, min(world.rows - 2, ty))
                    mob = generate_monster(tx * TILE_SIZE, ty * TILE_SIZE,
                                           sprites, db=db)
                    world.entities.append(mob)
                    status_msg = f"F3: Появился {mob.name}!"
                elif event.key == pygame.K_F4:
                    interiors_cache.clear()
                    dungeons_cache.clear()
                    cities_cache.clear()
                    loc_stack.clear()
                    world_seed = random.randint(0, 2 ** 31 - 1)
                    world, world_seed = make_world(sprites, db, player,
                                                   seed=world_seed)
                    outdoor_world = world
                    camera = Camera(world.width, world.height)
                    ui = UIManager(player, world.entities,
                                   sprites.get("loot"), sprites)
                    home_pos = world.spawn_pos
                    status_msg = f"F4: Мир перегенерирован! seed={world_seed}"

                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3,
                                   pygame.K_4, pygame.K_5, pygame.K_6) and player.skills:
                    slot_idx = event.key - pygame.K_1
                    mx, my = pygame.mouse.get_pos()
                    aim = (mx // SCALE + camera.offset_x,
                           my // SCALE + camera.offset_y)
                    _, msg = player.skills.use_active_slot(slot_idx, world,
                                                           aim_pos=aim)
                    if msg:
                        status_msg = msg
                elif event.key in (pygame.K_q, pygame.K_f, pygame.K_z,
                                   pygame.K_x):
                    q_map = {pygame.K_q: 0, pygame.K_f: 1, pygame.K_z: 2,
                             pygame.K_x: 3}
                    msg = player.use_quick_item(q_map[event.key])
                    if msg:
                        status_msg = msg
                elif event.key == pygame.K_SPACE and player.combat:
                    mx, my = pygame.mouse.get_pos()
                    aim = (mx // SCALE + camera.offset_x,
                           my // SCALE + camera.offset_y)
                    player.combat.attack(world, aim_pos=aim)

                elif event.key == pygame.K_e:
                    # 1) Сущности: NPC, сундуки
                    handled = False
                    for ent in world.entities:
                        if ent is not player and player.rect.inflate(18, 18).colliderect(ent.rect):
                            msg = ent.interact(player, ui)
                            if msg:
                                status_msg = msg
                                handled = True
                                break
                    if handled:
                        continue

                    # 2) Ворота городов, двери зданий, входы в пещеры
                    for bld in getattr(world, "buildings", []):
                        if bld.door_rect is None or not player.rect.colliderect(bld.door_rect):
                            continue
                        if bld.kind == "city_gate":
                            idx = bld.meta.get("city_idx", 0)
                            city = outdoor_world.cities[idx]
                            key = city["name"]
                            if key not in cities_cache:
                                cities_cache[key] = generate_city(
                                    city, sprites, player.rect.topleft,
                                    db=db, rng=random.Random(hash(key)))
                            status_msg = enter_map(
                                cities_cache[key],
                                f"Вы вошли: {city['name']} "
                                "([E] у нижних ворот — выйти)")
                        elif bld.kind == "cave":
                            depth = bld.meta.get("depth", 1)
                            if bld.id not in dungeons_cache:
                                dungeons_cache[bld.id] = generate_dungeon(
                                    depth=depth,
                                    return_pos=player.rect.topleft,
                                    sprites=sprites, db=db,
                                    rng=random.Random(hash(bld.id)),
                                    size=40 + depth * 6)
                            status_msg = enter_map(
                                dungeons_cache[bld.id],
                                f"Вы спустились: Подземелье (глубина {depth}). "
                                "[E] у лестницы внизу — выйти.")
                        else:
                            if bld.id not in interiors_cache:
                                interiors_cache[bld.id] = generate_interior(
                                    bld, sprites, player.rect.topleft, db=db)
                            status_msg = enter_map(
                                interiors_cache[bld.id],
                                f"Вы вошли: {bld.name} ([E] у двери — выйти)")
                        player.rect.topleft = world.spawn_pos
                        if player.movement:
                            player.movement.pos_x = float(player.rect.x)
                            player.movement.pos_y = float(player.rect.y)
                        camera = Camera(world.width, world.height)
                        handled = True
                        break
                    if handled:
                        continue

                    # 3) Выход из под-локации (интерьер, город, подземелье)
                    if getattr(world, "exit_rect", None) and player.rect.colliderect(world.exit_rect):
                        ret_pos = world.return_pos
                        world = loc_stack.pop() if loc_stack else outdoor_world
                        player.rect.topleft = ret_pos
                        if player.movement:
                            player.movement.pos_x = float(player.rect.x)
                            player.movement.pos_y = float(player.rect.y)
                        camera = Camera(world.width, world.height)
                        status_msg = "Вы вышли наружу."
                        continue

                    # 4) Интерактивная мебель
                    for prop_rect, p_kind, _ in getattr(world, "interactive_props", []):
                        if player.rect.colliderect(prop_rect):
                            if p_kind == "bed":
                                player.stats.hp = float(player.stats.max_hp)
                                player.stats.mp = float(player.stats.max_mp)
                                status_msg = "Вы отдохнули: HP и MP полны!"
                            elif p_kind == "workbench":
                                ui.open_professions()
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
                status_msg = "ГЕРОЙ ПАЛ! Удерживайте R для возрождения."
                if keys[pygame.K_r]:
                    player.respawn()
                    # Возрождение всегда на поверхности, у ворот столицы
                    loc_stack.clear()
                    if world is not outdoor_world:
                        world = outdoor_world
                        camera = Camera(world.width, world.height)
                    player.rect.topleft = home_pos
                    if player.movement:
                        player.movement.pos_x = float(player.rect.x)
                        player.movement.pos_y = float(player.rect.y)
                    status_msg = "Герой возрожден в столице!"

        native_surface.fill((15, 18, 24))
        camera.follow(player)
        if not ui.is_open and player.stats.hp > 0:
            mx, my = pygame.mouse.get_pos()
            player.facing_left = ((mx // SCALE + camera.offset_x) < player.rect.centerx)

        world.draw(native_surface, sprites, camera, None)

        # Подсказка биома под игроком
        biome_txt = ""
        if world is outdoor_world:
            biome_txt = f" [{world.biome_name_at(player.rect.centerx, player.rect.centery)}]"

        screen.blit(pygame.transform.scale(native_surface,
                                           (WINDOW_WIDTH, WINDOW_HEIGHT)), (0, 0))
        world.draw_speeches(screen, camera, SCALE, speech_font)
        if show_map and world is outdoor_world:
            draw_minimap(screen, world, player)
        if not ui.is_open:
            draw_hud(screen, player, status_msg + biome_txt, hud_font, sprites)
        ui.draw(screen)
        pygame.display.flip()


if __name__ == "__main__":
    run_test_world_gen()
