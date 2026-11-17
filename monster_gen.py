import random
import pygame
from entities import Entity
from items import ITEMS_DB
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.ai import AIController

# Цветовые схемы мутаций: (Префикс, Основной цвет, Тень, Цвет глаз, Бонусы: hp, atk, def, speed)
COLOR_VARIANTS = {
    "goblin": [
        ("Болотный", (95, 165, 60), (60, 110, 40), (220, 50, 50), {"hp": 0, "atk": 0, "def": 0, "spd": 0}),
        ("Пещерный", (130, 115, 95), (85, 75, 60), (255, 210, 50), {"hp": 10, "atk": 1, "def": 1, "spd": -5}),
        ("Кровавый", (185, 55, 55), (125, 35, 35), (255, 255, 255), {"hp": 15, "atk": 3, "def": 0, "spd": 10}),
        ("Теневой", (75, 70, 105), (45, 40, 65), (120, 230, 255), {"hp": 5, "atk": 2, "def": 0, "spd": 15}),
    ],
    "skeleton": [
        ("Древний", (215, 210, 195), (155, 150, 135), (220, 50, 50), {"hp": 0, "atk": 1, "def": 1, "spd": 0}),
        ("Ледяной", (140, 210, 235), (85, 145, 175), (50, 100, 255), {"hp": 15, "atk": 1, "def": 2, "spd": -5}),
        ("Проклятый", (145, 120, 165), (95, 75, 115), (100, 255, 100), {"hp": 20, "atk": 2, "def": 1, "spd": 5}),
    ],
    "slime": [
        ("Лесной", (70, 190, 90), (40, 130, 60), (20, 20, 28), {"hp": 10, "atk": 0, "def": 1, "spd": -10}),
        ("Огненный", (230, 100, 40), (170, 55, 20), (255, 240, 120), {"hp": 15, "atk": 3, "def": 0, "spd": 0}),
        ("Ядовитый", (160, 70, 200), (105, 40, 140), (150, 255, 80), {"hp": 10, "atk": 2, "def": 1, "spd": 5}),
    ]
}

# Запчасти 16x16: 'K' - контур, '1' - основной цвет, '2' - тень, 'E' - глаза, 'B' - кость/рога/зубы, 'A' - одежда/броня
PARTS = {
    # --- ГОЛОВЫ ГУМАНОИДОВ ---
    "head_goblin": [
        "................",
        "....KKKKKKKK....",
        "..KKK111111KKK..",
        ".K11KE1111EK11K.",
        "..KKK111111KKK..",
        "....K1KKKKKK....",
        ".....KKKKKK.....",
        "................",
    ],
    "head_goblin_horned": [
        "..KK........KK..",
        "..KBKKKKKKKKBK..",
        "...KK111111KK...",
        "..K1KE1111EK1K..",
        "...KK111111KK...",
        "....K1KKKKKK....",
        ".....KKKKKK.....",
        "................",
    ],
    "head_skull": [
        "................",
        ".....KKKKKK.....",
        "....K111111K....",
        "....K1E11E1K....",
        "....K112211K....",
        ".....K1K1KK.....",
        ".....KKKKKK.....",
        "................",
    ],
    "head_skull_crown": [
        "....K.K..K.K....",
        "....KBBBBBBK....",
        "....K111111K....",
        "....K1E11E1K....",
        "....K112211K....",
        ".....K1K1KK.....",
        ".....KKKKKK.....",
        "................",
    ],

    # --- ТЕЛА И НОГИ ГУМАНОИДОВ ---
    "body_rags": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "...KKAAAAAAKK...",
        "..KAAAAAAAAAAK..",
        "..K11KAAAAK11K..",
        "..KK.KBBBBK.KK..",
        ".....K2222K.....",
        ".....K2222K.....",
        ".....KK..KK.....",
        "....KKK..KKK....",
        "................",
    ],
    "body_ribcage": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "....KKKKKKKK....",
        "...K1K1111K1K...",
        "...K1K2222K1K...",
        "...KK.K11K.KK...",
        ".....K1..1K.....",
        ".....K2..2K.....",
        ".....KK..KK.....",
        "....KKK..KKK....",
        "................",
    ],
    # --- ТЕЛА СЛИЗНЕЙ (ЦЕЛЬНЫЕ) ---
    "slime_round": [
        "................",
        "................",
        "................",
        "................",
        "......KKKK......",
        "....KK1111KK....",
        "...K11111111K...",
        "..K11E1111E11K..",
        "..K1111111111K..",
        ".K111222222111K.",
        ".K112222222211K.",
        "..KKKKKKKKKKKK..",
        "................",
        "................",
        "................",
        "................",
    ],
    "slime_spiky": [
        "................",
        ".......KK.......",
        ".....KK11KK.....",
        "....K111111K....",
        "..KK11111111KK..",
        ".K111111111111K.",
        "..K11E1111E11K..",
        "..K1111111111K..",
        ".K111222222111K.",
        ".K112222222211K.",
        "..KKKKKKKKKKKK..",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
}

def assemble_monster_sprite(part_names, main_color, shade_color, eye_color):
    """Накладывает выбранные запчасти друг на друга и красит в нужный подвид"""
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    local_palette = {
        'K': (20, 20, 28),
        '1': main_color,
        '2': shade_color,
        'E': eye_color,
        'B': (225, 215, 185),  # Кости / рога / пояс
        'A': (105, 65, 40),    # Лохмотья / кожа
    }
    for part_key in part_names:
        matrix = PARTS[part_key]
        for y, row in enumerate(matrix):
            for x, char in enumerate(row):
                color = local_palette.get(char)
                if color:
                    surf.set_at((x, y), color)
    return surf

def generate_monster(x, y, sprite_bank):
    """Генерирует тематически согласованного уникального монстра"""
    archetype = random.choice(["goblin", "skeleton", "slime"])
    prefix, c_main, c_shade, c_eye, bonus = random.choice(COLOR_VARIANTS[archetype])

    if archetype == "goblin":
        head = random.choice(["head_goblin", "head_goblin_horned"])
        body = "body_rags"
        base_name = "Гоблин-вождь" if "horned" in head else "Гоблин"
        parts = [body, head]
        base_hp, base_atk, base_def, base_spd = 40, 4, 0, 45

    elif archetype == "skeleton":
        head = random.choice(["head_skull", "head_skull_crown"])
        body = "body_ribcage"
        base_name = "Король скелетов" if "crown" in head else "Скелет"
        parts = [body, head]
        base_hp, base_atk, base_def, base_spd = 45, 5, 1, 40

    else:  # slime
        body = random.choice(["slime_round", "slime_spiky"])
        base_name = "Шипастый слизень" if "spiky" in body else "Слизень"
        parts = [body]
        base_hp, base_atk, base_def, base_spd = 55, 4, 1, 30

    full_name = f"{prefix} {base_name.lower()}"
    sprite = assemble_monster_sprite(parts, c_main, c_shade, c_eye)

    # Создаем сущность с модулями
    mob = Entity(full_name, x, y, c_main, sprite=sprite, faction="monster", sprite_bank=sprite_bank)
    mob.movement = Movement(mob, speed=max(20, base_spd + bonus["spd"]))
    mob.inventory = Inventory(capacity=6, gold=random.randint(15, 50))
    mob.equipment = Equipment()
    mob.stats = Stats(
        hp=base_hp + bonus["hp"],
        mp=20,
        str_val=base_atk + bonus["atk"],
        agi_val=base_atk + bonus["atk"],
        end_val=base_def + bonus["def"]
    )

    mob.combat = Combat(mob, cooldown=0.75)
    mob.ai = AIController(mob, role="monster", aggro_radius=90)
    mob.link_components()

    # Выдаем тематический лут и оружие (гуманоидам - мечи, слизням - самоцветы и зелья)
    if archetype in ("goblin", "skeleton"):
        weapon_choice = random.choice(["rusty_sword", "rusty_sword", "iron_sword"])
        mob.inventory.add_item(ITEMS_DB[weapon_choice])
        if random.random() < 0.4:
            mob.inventory.add_item(ITEMS_DB["leather_armor"])
    else:
        mob.inventory.add_item(ITEMS_DB["gem"])

    if random.random() < 0.6:
        mob.inventory.add_item(ITEMS_DB["potion"])

    return mob
