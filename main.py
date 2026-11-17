import pygame
import sys
from settings import *
from items import ITEMS_DB
from entities import Entity
from sprites import load_sprites
from ui import UIManager
from world import WorldMap, Camera
from monster_gen import generate_monster
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.ai import AIController
from components.skills import SkillBook

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    native_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
    pygame.display.set_caption("8-Bit Modular RPG - Town Square")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 9)
    small_font = pygame.font.SysFont("monospace", 8)

    sprites = load_sprites()
    world = WorldMap(cols=40, rows=25)
    walls = world.walls
    camera = Camera(world.width, world.height)

    # 1. ИГРОК (На центральной площади из брусчатки)
    player = Entity("Герой", 180, 150, COLOR_PLAYER, sprite=sprites["player"], faction="player", sprite_bank=sprites)
    player.movement = Movement(player, speed=80)
    player.inventory = Inventory(capacity=4, gold=150)
    player.equipment = Equipment()
    player.stats = Stats(hp=70, mp=45, str_val=4, agi_val=3, int_val=4, vit_val=3, end_val=1)
    player.combat = Combat(player, cooldown=0.4)
    player.skills = SkillBook(player, max_slots=4)
    player.link_components()

    # 2. ТОРГОВЕЦ (На торговой брусчатке)
    merchant = Entity("Торговец", 240, 130, COLOR_NPC, sprite=sprites["npc"], faction="town", sprite_bank=sprites)
    merchant.movement = Movement(merchant, speed=30)
    merchant.inventory = Inventory(capacity=18, gold=300)
    merchant.equipment = Equipment()
    merchant.stats = Stats(hp=50, mp=10, str_val=2, end_val=0)
    merchant.ai = AIController(merchant, role="merchant")
    merchant.link_components()
    merchant.inventory.add_item(ITEMS_DB["book_whirlwind"])
    merchant.inventory.add_item(ITEMS_DB["book_ice"])
    merchant.inventory.add_item(ITEMS_DB["book_heal"])
    merchant.inventory.add_item(ITEMS_DB["book_blade"])
    merchant.inventory.add_item(ITEMS_DB["fire_staff"])
    merchant.inventory.add_item(ITEMS_DB["hunting_bow"])
    merchant.inventory.add_item(ITEMS_DB["iron_sword"])
    merchant.inventory.add_item(ITEMS_DB["small_bag"])
    merchant.inventory.add_item(ITEMS_DB["potion"])
    merchant.inventory.add_item(ITEMS_DB["mana_potion"])

    # 3. СТРАЖНИК (Патрулирует площадь)
    guard = Entity("Стражник", 280, 155, (180, 60, 60), sprite=sprites["guard"], faction="town", sprite_bank=sprites)
    guard.movement = Movement(guard, speed=50)
    guard.inventory = Inventory(capacity=6, gold=20)
    guard.equipment = Equipment()
    guard.stats = Stats(hp=70, mp=30, str_val=6, vit_val=2, end_val=2)
    guard.combat = Combat(guard, cooldown=0.5)
    guard.skills = SkillBook(guard, max_slots=4)
    guard.ai = AIController(guard, role="guard", aggro_radius=110)
    guard.link_components()
    guard.inventory.add_item(ITEMS_DB["iron_sword"])
    guard.inventory.add_item(ITEMS_DB["chainmail"])
    guard.inventory.add_item(ITEMS_DB["book_whirlwind"])
    guard.inventory.add_item(ITEMS_DB["potion"])

    # 4. ПРИКЛЮЧЕНЕЦ (Ищет приключения на южной тропинке)
    adventurer = Entity("Странник", 210, 270, (70, 130, 210), sprite=sprites["adventurer"], faction="adventurer", sprite_bank=sprites)
    adventurer.movement = Movement(adventurer, speed=55)
    adventurer.inventory = Inventory(capacity=8, gold=40)
    adventurer.equipment = Equipment()
    adventurer.stats = Stats(hp=55, mp=40, str_val=4, agi_val=4, int_val=4, vit_val=2, end_val=1)
    adventurer.combat = Combat(adventurer, cooldown=0.5)
    adventurer.skills = SkillBook(adventurer, max_slots=4)
    adventurer.ai = AIController(adventurer, role="adventurer", aggro_radius=110)
    adventurer.link_components()
    adventurer.inventory.add_item(ITEMS_DB["rusty_sword"])
    adventurer.inventory.add_item(ITEMS_DB["book_ice"])
    adventurer.inventory.add_item(ITEMS_DB["potion"])

    # 5. ГОБЛИН-ЛУЧНИК (Бродит возле песчаного берега озера справа)
    goblin = Entity("Гоблин-лучник", 420, 210, (100, 180, 60), sprite=sprites["goblin"], faction="monster", sprite_bank=sprites)
    goblin.movement = Movement(goblin, speed=45)
    goblin.inventory = Inventory(capacity=6, gold=35)
    goblin.equipment = Equipment()
    goblin.stats = Stats(hp=35, mp=30, str_val=3, agi_val=5, end_val=0)
    goblin.combat = Combat(goblin, cooldown=0.8)
    goblin.skills = SkillBook(goblin, max_slots=4)
    goblin.ai = AIController(goblin, role="monster", aggro_radius=110)
    goblin.link_components()
    goblin.inventory.add_item(ITEMS_DB["hunting_bow"])
    goblin.inventory.add_item(ITEMS_DB["book_volley"])
    goblin.inventory.add_item(ITEMS_DB["gem"])

    # 6. СУНДУК (У южной дороги)
    chest = Entity("Сундук", 230, 310, COLOR_CHEST, sprite=sprites["chest"], is_container=True)
    chest.inventory = Inventory(capacity=6, gold=25)
    chest.inventory.add_item(ITEMS_DB["leather_armor"])
    chest.inventory.add_item(ITEMS_DB["book_skin"])
    chest.inventory.add_item(ITEMS_DB["book_mana"])
    entities = [player, merchant, guard, adventurer, goblin, chest]
    projectiles = []
    ui = UIManager(player)
    status_msg = "I: Рюкзак | K: Навыки | 1/2: Умения | C: Статы | E: Торг/Лут | M: Моб"

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

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_i, pygame.K_TAB):
                    ui.open_inventory()
                elif event.key == pygame.K_c:
                    ui.open_stats()
                elif event.key == pygame.K_k:
                    ui.open_skills()
                elif event.key == pygame.K_1 and player.skills:
                    _, msg = player.skills.use_active_slot(0, entities, projectiles, walls)
                    if msg:
                        status_msg = msg
                elif event.key == pygame.K_2 and player.skills:
                    _, msg = player.skills.use_active_slot(1, entities, projectiles, walls)
                    if msg:
                        status_msg = msg
                elif event.key == pygame.K_l:
                    if player.stats.gain_xp(60):
                        status_msg = f"НОВЫЙ УРОВЕНЬ {player.stats.level}! Нажми C!"
                    else:
                        status_msg = f"Опыт +60 ({player.stats.xp}/{player.stats.xp_to_next})"
                elif event.key == pygame.K_SPACE and player.combat:
                    player.combat.attack(entities, projectiles, walls=walls)
                elif event.key == pygame.K_m:
                    # Спавним случайного монстра на восточной окраине у озера
                    new_mob = generate_monster(460, 180, sprites)
                    entities.append(new_mob)
                    status_msg = f"Появился: {new_mob.name}!"
                elif event.key == pygame.K_e:
                    for ent in entities:
                        if ent is player:
                            continue
                        if player.rect.inflate(16, 16).colliderect(ent.rect):
                            if ent.is_container and ent.inventory:
                                gold_found = ent.inventory.gold
                                ui.open_container(ent, "chest")
                                if gold_found > 0:
                                    status_msg = f"Найдено золота: +{gold_found}G!"
                                break
                            elif ent.ai and ent.ai.role == "merchant" and ent.inventory:
                                ui.open_container(ent, "trade")
                                break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and player.combat:
                mx, my = event.pos
                # Переводим координаты мыши в мировые с учетом смещения камеры!
                aim = (mx // SCALE + camera.offset_x, my // SCALE + camera.offset_y)
                player.combat.attack(entities, projectiles, aim_pos=aim, walls=walls)

        if not ui.is_open:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if player.movement:
                move_dt = dt * 0.5 if getattr(player, "slow_timer", 0) > 0 else dt
                player.movement.move(dx, dy, move_dt, walls)

            for ent in list(entities):
                ent.update(dt, walls, entities, projectiles)

                if ent is not player and ent.stats and ent.stats.hp <= 0:
                    loot_bag = ent.drop_loot_bag(sprites["loot"])
                    entities.remove(ent)
                    entities.append(loot_bag)
                    if ent.last_attacker and ent.last_attacker.stats:
                        leveled = ent.last_attacker.stats.gain_xp(50)
                        if ent.last_attacker is player:
                            if leveled:
                                status_msg = f"УРОВЕНЬ {player.stats.level}! Нажми C (Очков: {player.stats.stat_points})"
                            else:
                                status_msg = f"{ent.name} побежден! (+50 XP)"
                        else:
                            status_msg = f"{ent.name} пал от руки {ent.last_attacker.name}!"

            for proj in list(projectiles):
                proj.update(dt, walls, entities)
                if not proj.alive:
                    projectiles.remove(proj)

            if player.stats.hp <= 0:
                status_msg = "ВЫ ПОГИБЛИ! Нажми R для возрождения"
                if keys[pygame.K_r]:
                    player.stats.hp = float(player.stats.max_hp)
                    player.stats.mp = float(player.stats.max_mp)
                    player.rect.topleft = (180, 150)
                    player.movement.pos_x, player.movement.pos_y = 180.0, 150.0
                    status_msg = "Герой возрожден!"

        # Обновляем позицию камеры за игроком
        camera.follow(player)

        # Отрисовка мира с учетом камеры
        world.draw(native_surface, sprites, camera, small_font)

        # Отрисовываем сущности со сдвигом камеры (временно сдвигаем rect для отрисовки)
        for ent in sorted(entities, key=lambda e: e.rect.bottom):
            orig_pos = ent.rect.topleft
            ent.rect.x -= camera.offset_x
            ent.rect.y -= camera.offset_y
            if ent.combat and ent.combat.swing_rect:
                ent.combat.swing_rect.x -= camera.offset_x
                ent.combat.swing_rect.y -= camera.offset_y

            ent.draw(native_surface, small_font)

            ent.rect.topleft = orig_pos
            if ent.combat and ent.combat.swing_rect:
                ent.combat.swing_rect.x += camera.offset_x
                ent.combat.swing_rect.y += camera.offset_y

        # Отрисовка снарядов со сдвигом камеры
        for proj in projectiles:
            proj.pos_x -= camera.offset_x
            proj.pos_y -= camera.offset_y
            proj.draw(native_surface)
            proj.pos_x += camera.offset_x
            proj.pos_y += camera.offset_y

        if not ui.is_open:
            mx, my = pygame.mouse.get_pos()
            cx, cy = mx // SCALE, my // SCALE
            pygame.draw.line(native_surface, (255, 220, 90), (cx - 3, cy), (cx + 3, cy), 1)
            pygame.draw.line(native_surface, (255, 220, 90), (cx, cy - 3), (cx, cy + 3), 1)

            pygame.draw.rect(native_surface, (15, 18, 24), (0, NATIVE_HEIGHT - 15, NATIVE_WIDTH, 15))
            hp_txt = font.render(f"HP:{int(player.stats.hp)}/{player.stats.max_hp}", False, (100, 220, 120))
            mp_txt = font.render(f"MP:{int(player.stats.mp)}/{player.stats.max_mp}", False, (90, 170, 255))
            native_surface.blit(hp_txt, (4, NATIVE_HEIGHT - 13))
            native_surface.blit(mp_txt, (56, NATIVE_HEIGHT - 13))

            if player.stats.stat_points > 0:
                pts_txt = font.render(f"[C]+{player.stats.stat_points}!", False, (255, 215, 60))
                native_surface.blit(pts_txt, (104, NATIVE_HEIGHT - 13))
                text_surf = font.render(status_msg, False, COLOR_TEXT)
                native_surface.blit(text_surf, (144, NATIVE_HEIGHT - 13))
            else:
                text_surf = font.render(status_msg, False, COLOR_TEXT)
                native_surface.blit(text_surf, (104, NATIVE_HEIGHT - 13))

        scaled_surface = pygame.transform.scale(native_surface, (WINDOW_WIDTH, WINDOW_HEIGHT))
        screen.blit(scaled_surface, (0, 0))
        ui.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()
