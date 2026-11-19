import pygame
import sys
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, NATIVE_WIDTH, NATIVE_HEIGHT, SCALE, FPS, COLOR_TEXT
from sprites import load_sprites
from ui import UIManager
from world import WorldMap, Camera
from char_creator import CharacterCreator
from menus import MainMenu, PauseMenu
from monster_gen import generate_monster
from database import DatabaseManager
from hud import draw_hud

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.scrap.init()
    native_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
    pygame.display.set_caption("8-Bit Modular RPG")
    clock = pygame.time.Clock()
    hud_font = pygame.font.SysFont("consolas", 17, bold=True)
    speech_font = pygame.font.SysFont("consolas", 15, bold=True)

    db = DatabaseManager("rpg.db")
    db.sync_all_catalogs()
    sprites = load_sprites(db)

    main_menu = MainMenu(db)
    pause_menu = PauseMenu(db)

    game_state = "MENU"
    creator, world, player, camera, ui = None, None, None, None, None
    autosave_timer = 0.0
    status_msg = "F5: Быстр.сейв | I: Рюкзак | J: Квесты | K: Навыки | E: Действие | ESC: Пауза"
    while True:
        dt = clock.tick(db.settings.get("target_fps", FPS)) / 1000.0

        if game_state == "MENU":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                res = main_menu.handle_event(event)
                if res:
                    action, slot_val = res
                    if action == "new_game":
                        creator = CharacterCreator(sprites, db)
                        game_state = "CREATOR"
                    elif action == "do_load":
                        world, player, msg = db.load_world(sprites, slot_id=slot_val)
                        if world and player:
                            camera = Camera(world.width, world.height)
                            ui = UIManager(player, world.entities, sprites.get("loot"), sprites)
                            autosave_timer = 0.0
                            status_msg = msg
                            game_state = "PLAYING"
                        else:
                            main_menu.notice = msg
                    elif action == "quit":
                        pygame.quit()
                        sys.exit()
            main_menu.draw(screen)
            pygame.display.flip()
            continue

        if game_state == "CREATOR":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state = "MENU"
                    break
                created = creator.handle_event(event)
                if created is not None:
                    player = created
                    world = WorldMap(cols=40, rows=25)
                    world.populate_town_square(sprites, player, db)
                    camera = Camera(world.width, world.height)
                    ui = UIManager(player, world.entities, sprites.get("loot"))
                    autosave_timer = 0.0
                    status_msg = f"Добро пожаловать, {player.name}! (ESC — Пауза)"
                    game_state = "PLAYING"
                    break
            if game_state == "CREATOR":
                creator.draw(screen)
                pygame.display.flip()
            continue

        if game_state == "PAUSE":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                res = pause_menu.handle_event(event)
                if res:
                    action, slot_val = res
                    if action == "resume":
                        pause_menu.notice = ""
                        game_state = "PLAYING"
                    elif action == "do_save":
                        _, msg = db.save_world(world, player, sprites, slot_id=None if slot_val == "new_slot" else slot_val, slot_type="manual")
                        pause_menu.notice = msg
                    elif action == "do_load":
                        loaded_w, loaded_p, msg = db.load_world(sprites, slot_id=slot_val)
                        if loaded_w and loaded_p:
                            world, player = loaded_w, loaded_p
                            camera = Camera(world.width, world.height)
                            ui = UIManager(player, world.entities, sprites.get("loot"))
                            autosave_timer = 0.0
                            status_msg = msg
                            pause_menu.notice = ""
                            game_state = "PLAYING"
                        else:
                            pause_menu.notice = msg
                    elif action == "to_main":
                        pause_menu.notice = ""
                        main_menu.cursor = 0
                        game_state = "MENU"
                    elif action == "quit":
                        pygame.quit()
                        sys.exit()
            screen.blit(pygame.transform.scale(native_surface, (WINDOW_WIDTH, WINDOW_HEIGHT)), (0, 0))
            pause_menu.draw(screen)
            pygame.display.flip()
            continue

        # --- ИГРОВОЙ ПРОЦЕСС ---
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
                    pause_menu.cursor = 0
                    pause_menu.notice = ""
                    game_state = "PAUSE"
                    continue
                elif event.key == pygame.K_F5:
                    _, status_msg = db.save_world(world, player, sprites, slot_type="quick")
                elif event.key == pygame.K_F9:
                    loaded_w, loaded_p, msg = db.load_world(sprites, slot_id=0)
                    if loaded_w and loaded_p:
                        world, player = loaded_w, loaded_p
                        camera = Camera(world.width, world.height)
                        ui = UIManager(player, world.entities, sprites.get("loot"))
                    status_msg = msg
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
                elif event.key == pygame.K_m:
                    new_mob = generate_monster(460, 180, sprites, db=db)
                    world.entities.append(new_mob)
                    status_msg = f"Появился: {new_mob.name}!"
                elif event.key == pygame.K_e:
                    for ent in world.entities:
                        if ent is not player and player.rect.inflate(16, 16).colliderect(ent.rect):
                            msg = ent.interact(player, ui)
                            if msg:
                                status_msg = msg
                                break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and player.combat:
                mx, my = event.pos
                aim = (mx // SCALE + camera.offset_x, my // SCALE + camera.offset_y)
                player.combat.attack(world, aim_pos=aim)

        if not ui.is_open:
            auto_min = db.settings.get("autosave_minutes", 0)
            if auto_min > 0 and player.stats.hp > 0:
                autosave_timer += dt
                if autosave_timer >= auto_min * 60:
                    autosave_timer = 0.0
                    _, status_msg = db.save_world(world, player, sprites, slot_type="auto")

            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if player.movement:
                player.movement.move(dx, dy, dt, world.walls)

            world_msg = world.update(dt, player, ui, sprites.get("loot"))
            if world_msg:
                status_msg = world_msg

            if player.stats.hp <= 0:
                status_msg = "ВЫ ПОГИБЛИ! R: Возродиться | F9: Загрузить"
                if keys[pygame.K_r]:
                    player.respawn()
                    status_msg = "Герой возрожден!"

        native_surface.fill((15, 18, 24))
        camera.follow(player)
        if not ui.is_open and player.stats.hp > 0:
            mx, my = pygame.mouse.get_pos()
            world_mx = mx // SCALE + camera.offset_x
            player.facing_left = (world_mx < player.rect.centerx)
        world.draw(native_surface, sprites, camera, None)

        screen.blit(pygame.transform.scale(native_surface, (WINDOW_WIDTH, WINDOW_HEIGHT)), (0, 0))
        if db.settings.get("show_speech", True):
            world.draw_speeches(screen, camera, SCALE, speech_font)
        if not ui.is_open:
            draw_hud(screen, player, status_msg, hud_font, sprites)
        ui.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()
