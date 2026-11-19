import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_TEXT
from items import ITEMS_DB

QUICK_KEYS_LABELS = ["Q", "F", "Z", "X"]
_ICON_CACHE = {}

def get_skill_icon(skill, sprites):
    if skill.sprite_key and skill.sprite_key in sprites:
        return sprites[skill.sprite_key]
    custom_key = f"skill_{skill.id}"
    if custom_key in sprites:
        return sprites[custom_key]
    if custom_key in _ICON_CACHE:
        return _ICON_CACHE[custom_key]

    # Авто-генерация 8-битной рунической иконки 16x16 для навыка
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    col_map = {
        "whirlwind": ((220, 90, 70), (255, 200, 120)),
        "volley": ((90, 195, 95), (200, 245, 160)),
        "ice_bolt": ((70, 175, 245), (200, 245, 255)),
        "heal_spell": ((240, 200, 65), (255, 250, 190)),
        "race_elf": ((80, 220, 160), (200, 255, 230)),
        "race_skeleton": ((165, 85, 210), (235, 170, 255)),
    }
    main_c, glow_c = col_map.get(skill.id, ((110, 150, 220), (200, 225, 255)))
    pygame.draw.rect(surf, (20, 20, 28), (2, 2, 12, 12))
    pygame.draw.rect(surf, main_c, (3, 3, 10, 10))
    pygame.draw.rect(surf, glow_c, (6, 6, 4, 4))
    _ICON_CACHE[custom_key] = surf
    return surf

def get_item_icon(item, sprites):
    if item.sprite_key and item.sprite_key in sprites:
        return sprites[item.sprite_key]
    custom_key = f"item_{item.id}"
    if custom_key in sprites:
        return sprites[custom_key]
    if custom_key in _ICON_CACHE:
        return _ICON_CACHE[custom_key]

    # Авто-генерация 8-битной иконки 16x16 для зелий и свитков
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    if "expand_skill_slots" in item.stats_bonus:
        # Свиток расширения памяти
        pygame.draw.rect(surf, (20, 20, 28), (3, 2, 10, 12))
        pygame.draw.rect(surf, (235, 215, 160), (4, 3, 8, 10))
        pygame.draw.rect(surf, (155, 80, 210), (6, 6, 4, 4))
    else:
        # Алхимическая колба
        liq_col = (220, 60, 60)
        if "mana" in item.stats_bonus:
            liq_col = (60, 145, 240)
        elif item.stats_bonus.get("effect") == "haste":
            liq_col = (240, 205, 60)
        elif item.stats_bonus.get("effect") == "shield":
            liq_col = (130, 150, 245)
        elif item.stats_bonus.get("cure"):
            liq_col = (75, 205, 90)
        pygame.draw.rect(surf, (20, 20, 28), (6, 2, 4, 3))
        pygame.draw.rect(surf, (180, 130, 70), (7, 2, 2, 2))
        pygame.draw.rect(surf, (20, 20, 28), (4, 5, 8, 9))
        pygame.draw.rect(surf, liq_col, (5, 6, 6, 7))
        pygame.draw.rect(surf, (255, 255, 255), (6, 7, 2, 2))

    _ICON_CACHE[custom_key] = surf
    return surf

def get_quick_slot_rects(player, in_inventory=False):
    slot_size = 46
    gap = 8
    num_item_slots = len(getattr(player, "quick_items", [None, None, None, None]))

    if in_inventory:
        start_x = 890
        panel_y = 580
        return [
            pygame.Rect(start_x + i * (slot_size + gap), panel_y, slot_size, slot_size)
            for i in range(num_item_slots)
        ]

    bar_h = 34
    panel_y = WINDOW_HEIGHT - bar_h - slot_size - 10
    num_skill_slots = player.skills.max_active_slots if player.skills else 2
    skills_w = num_skill_slots * slot_size + (num_skill_slots - 1) * gap
    items_w = num_item_slots * slot_size + (num_item_slots - 1) * gap
    divider_w = 24
    start_x = WINDOW_WIDTH // 2 - (skills_w + divider_w + items_w) // 2
    items_start_x = start_x + skills_w + divider_w

    return [
        pygame.Rect(items_start_x + i * (slot_size + gap), panel_y, slot_size, slot_size)
        for i in range(num_item_slots)
    ]

def draw_hud(screen, player, status_msg, hud_font, sprites):
    # 1. Прицел мыши
    mx, my = pygame.mouse.get_pos()
    pygame.draw.line(screen, (255, 220, 90), (mx - 8, my), (mx + 8, my), 2)
    pygame.draw.line(screen, (255, 220, 90), (mx, my - 8), (mx, my + 8), 2)

    # 2. Нижняя полоса статуса (HP, MP и сообщения)
    bar_h = 34
    pygame.draw.rect(screen, (15, 18, 24), (0, WINDOW_HEIGHT - bar_h, WINDOW_WIDTH, bar_h))
    pygame.draw.line(screen, (60, 70, 90), (0, WINDOW_HEIGHT - bar_h), (WINDOW_WIDTH, WINDOW_HEIGHT - bar_h), 1)

    hp_txt = hud_font.render(f"HP: {int(player.stats.hp)}/{player.stats.max_hp}", True, (100, 220, 120))
    mp_txt = hud_font.render(f"MP: {int(player.stats.mp)}/{player.stats.max_mp}", True, (90, 170, 255))
    screen.blit(hp_txt, (16, WINDOW_HEIGHT - 26))
    screen.blit(mp_txt, (170, WINDOW_HEIGHT - 26))

    if player.stats.stat_points > 0:
        pts_txt = hud_font.render(f"[C] +{player.stats.stat_points}!", True, (255, 215, 60))
        screen.blit(pts_txt, (320, WINDOW_HEIGHT - 26))
        screen.blit(hud_font.render(status_msg, True, COLOR_TEXT), (440, WINDOW_HEIGHT - 26))
    else:
        screen.blit(hud_font.render(status_msg, True, COLOR_TEXT), (320, WINDOW_HEIGHT - 26))

    # 3. Две панели быстрого доступа над нижней полосой
    slot_size = 46
    gap = 6
    panel_y = WINDOW_HEIGHT - bar_h - slot_size - 10

    num_skill_slots = player.skills.max_active_slots if player.skills else 2
    actives = player.skills.get_active_skills() if player.skills else []
    num_item_slots = len(getattr(player, "quick_items", [None, None, None, None]))

    skills_w = num_skill_slots * slot_size + (num_skill_slots - 1) * gap
    items_w = num_item_slots * slot_size + (num_item_slots - 1) * gap
    divider_w = 24
    total_w = skills_w + divider_w + items_w
    start_x = WINDOW_WIDTH // 2 - total_w // 2

    # --- ЛЕВАЯ ПАНЕЛЬ: АКТИВНЫЕ НАВЫКИ (1, 2, 3...) ---
    for i in range(num_skill_slots):
        sx = start_x + i * (slot_size + gap)
        rect = pygame.Rect(sx, panel_y, slot_size, slot_size)
        pygame.draw.rect(screen, (22, 26, 36), rect, border_radius=6)

        if i < len(actives):
            sk = actives[i]
            icon = pygame.transform.scale(get_skill_icon(sk, sprites), (32, 32))
            screen.blit(icon, (sx + 7, panel_y + 7))

            # Затемнение перезарядки (cooldown)
            if sk.timer > 0 and sk.cooldown > 0:
                ratio = min(1.0, sk.timer / sk.cooldown)
                cd_h = int(slot_size * ratio)
                cd_surf = pygame.Surface((slot_size, cd_h), pygame.SRCALPHA)
                cd_surf.fill((10, 12, 18, 185))
                screen.blit(cd_surf, (sx, panel_y + slot_size - cd_h))
                cd_txt = hud_font.render(f"{sk.timer:.1f}", True, (255, 220, 90))
                screen.blit(cd_txt, (rect.centerx - cd_txt.get_width() // 2, rect.centery - cd_txt.get_height() // 2))

            border_col = (100, 190, 255) if sk.timer <= 0 else (90, 100, 120)
        else:
            border_col = (60, 68, 85)

        pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)
        key_lbl = hud_font.render(str(i + 1), True, (230, 235, 245))
        screen.blit(key_lbl, (sx + 4, panel_y + 2))

    # --- ПРАВАЯ ПАНЕЛЬ: БЫСТРЫЕ ПРЕДМЕТЫ (Q, F, Z, X) ---
    items_start_x = start_x + skills_w + divider_w
    q_items = getattr(player, "quick_items", [None, None, None, None])

    draw_quick_items_bar(screen, player, hud_font, sprites)

def draw_quick_items_bar(screen, player, hud_font, sprites, in_inventory=False):
    if in_inventory:
        box = pygame.Rect(820, 515, 420, 145)
        pygame.draw.rect(screen, (20, 24, 34), box, border_radius=4)
        pygame.draw.rect(screen, (95, 105, 125), box, 2, border_radius=4)
        title = hud_font.render("БЫСТРЫЙ ДОСТУП (ПЕРЕТАЩИТЕ СЮДА)", True, (240, 195, 75))
        screen.blit(title, (box.x + 16, box.y + 12))
        pygame.draw.line(screen, (95, 105, 125), (box.x + 10, box.y + 44), (box.right - 10, box.y + 44), 2)

    rects = get_quick_slot_rects(player, in_inventory=in_inventory)
    q_items = getattr(player, "quick_items", [None, None, None, None])

    for i, rect in enumerate(rects):
        pygame.draw.rect(screen, (28, 34, 48), rect, border_radius=6)
        item_id = q_items[i]
        if item_id and item_id in ITEMS_DB:
            item_obj = ITEMS_DB[item_id]
            count = sum(1 for it in player.inventory.items if it.id == item_id) if player.inventory else 0
            icon = pygame.transform.scale(get_item_icon(item_obj, sprites), (32, 32))
            if count == 0:
                icon.set_alpha(90)
            screen.blit(icon, (rect.x + 7, rect.y + 7))

            cnt_col = (130, 235, 160) if count > 0 else (220, 90, 90)
            cnt_txt = hud_font.render(f"x{count}", True, cnt_col)
            screen.blit(cnt_txt, (rect.right - cnt_txt.get_width() - 3, rect.bottom - cnt_txt.get_height() - 1))
            border_col = (240, 195, 75) if count > 0 else (80, 85, 95)
        else:
            border_col = (80, 90, 110)

        pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)
        key_lbl = hud_font.render(QUICK_KEYS_LABELS[i], True, (230, 235, 245))
        screen.blit(key_lbl, (rect.x + 4, rect.y + 2))

