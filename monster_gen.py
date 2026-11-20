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
from components.skills import SkillBook
import json
from sprites import PALETTE




COLOR_THEMES = [
    ((85, 165, 65), (55, 115, 40), (240, 60, 60)),     # Болотный зеленый
    ((185, 65, 65), (130, 40, 40), (255, 220, 70)),    # Багровый
    ((75, 135, 205), (45, 90, 150), (140, 245, 255)),  # Ледяной синий
    ((145, 85, 185), (100, 50, 135), (120, 255, 120)), # Ядовитый фиолетовый
    ((205, 185, 145), (150, 130, 95), (255, 90, 50)),  # Костяной / Песчаный
]

MODIFIERS = [
    ("Обычный", {"hp": 0, "atk": 0, "spd": 0}),
    ("Дикий", {"hp": 5, "atk": 2, "spd": 10}),
    ("Бронированный", {"hp": 15, "atk": 0, "spd": -8}),
    ("Свирепый", {"hp": 10, "atk": 3, "spd": 5}),
    ("Древний", {"hp": 25, "atk": 4, "spd": -5}),
]


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

def assemble_monster_sprite(part_keys, body_c, dark_c, eye_c):
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    custom_pal = dict(PALETTE)
    custom_pal["M"] = body_c
    custom_pal["m"] = dark_c
    custom_pal["B"] = body_c
    custom_pal["b"] = dark_c
    custom_pal["E"] = eye_c

    fallback = {
        "body_ribcage": [
            "................", "................", "................", "................",
            "................", "................", ".....MMMMMM.....", "....M.MMMM.M....",
            "...M..mMMm..M...", "...M..MMMM..M...", ".....mMMMMm.....", ".....MM..MM.....",
            ".....mm..mm.....", "....MMM..MMM....", "................", "................"
        ],
        "head_skull": [
            "................", ".....MMMMMM.....", "....MMMMMMMM....", "....MMEmmEMM....",
            "....MMMMMMMM....", ".....MmMmMm.....", "................", "................",
            "................", "................", "................", "................",
            "................", "................", "................", "................"
        ]
    }

    for key in part_keys:
        matrix = PARTS.get(key) or fallback.get(key)
        if not matrix:
            continue
        for r_idx, row in enumerate(matrix[:16]):
            for c_idx, ch in enumerate(row[:16]):
                col = custom_pal.get(ch)
                if col:
                    surf.set_at((c_idx, r_idx), col)
    return surf


def generate_monster(x, y, sprite_bank, db=None):
    """Собирает уникального монстра из таблиц monster_archetypes и monster_parts базы данных"""
    archetypes_list = []
    parts_by_arch = {}

    if db is not None:
        cur = db.conn.cursor()
        cur.execute("SELECT * FROM monster_archetypes")
        archetypes_list = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM monster_parts")
        for r in cur.fetchall():
            arch = r["archetype"]
            parts_by_arch.setdefault(arch, {"body": [], "head": []})
            parts_by_arch[arch][r["part_type"]].append(json.loads(r["art_matrix"]))

    # Запасной вариант, если БД не передана
    if not archetypes_list:
        archetypes_list = [
            {"id": "goblin", "name_ru": "Гоблин", "base_hp": 30, "base_atk": 3, "speed": 45, "faction": "monster", "possible_skills": '["volley", "whirlwind"]'},
            {"id": "skeleton", "name_ru": "Скелет", "base_hp": 35, "base_atk": 4, "speed": 42, "faction": "undead", "possible_skills": '["ice_bolt", "heal_spell"]'},
            {"id": "slime", "name_ru": "Слизень", "base_hp": 42, "base_atk": 2, "speed": 35, "faction": "monster", "possible_skills": '["passive_skin"]'},
        ]

    arch_data = random.choice(archetypes_list)
    arch_id = arch_data["id"]
    base_name = arch_data["name_ru"]
    base_hp = arch_data["base_hp"]
    base_atk = arch_data["base_atk"]
    base_speed = arch_data["speed"]
    faction = arch_data["faction"]
    possible_skills = json.loads(arch_data["possible_skills"]) if isinstance(arch_data["possible_skills"], str) else arch_data["possible_skills"]

    mod_name, bonus = random.choice(MODIFIERS)
    full_name = f"{mod_name} {base_name}"

    arch_parts = parts_by_arch.get(arch_id, {})
    bodies = arch_parts.get("body", [])
    heads = arch_parts.get("head", [])

    if bodies:
        chosen_layers = [random.choice(bodies)]
        if heads:
            chosen_layers.append(random.choice(heads))
        # Собираем спрайт из выбранных матриц
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        body_c, dark_c, eye_c = random.choice(COLOR_THEMES)
        custom_pal = dict(PALETTE)
        custom_pal["M"] = body_c
        custom_pal["m"] = dark_c
        custom_pal["B"] = body_c
        custom_pal["b"] = dark_c
        custom_pal["E"] = eye_c

        for matrix in chosen_layers:
            for r_idx, row in enumerate(matrix[:16]):
                for c_idx, ch in enumerate(row[:16]):
                    col = custom_pal.get(ch)
                    if col:
                        surf.set_at((c_idx, r_idx), col)
        spr = surf
    else:
        spr = sprite_bank.get("goblin")

    mob = Entity(full_name, x, y, (180, 70, 70), sprite=spr, faction=faction, sprite_bank=sprite_bank)
    mob.movement = Movement(mob, speed=max(25, base_speed + bonus["spd"]))
    mob.inventory = Inventory(capacity=6, gold=random.randint(10, 45))
    mob.equipment = Equipment()
    mob.stats = Stats(
        hp=base_hp + bonus["hp"],
        mp=30,
        str_val=max(1, base_atk + bonus["atk"]),
        agi_val=max(1, base_atk + bonus["atk"]),
        int_val=max(1, base_atk + bonus["atk"]),
        end_val=1 if mod_name == "Бронированный" else 0
    )
    mob.combat = Combat(mob, cooldown=0.8)
    mob.ai = AIController(mob, role="monster", aggro_radius=115)
    mob.skills = SkillBook(mob, max_slots=4)
    mob.link_components()

    if possible_skills:
        k_count = min(len(possible_skills), random.randint(1, 2))
        for sk_id in random.sample(possible_skills, k=k_count):
            mob.skills.learn_skill(sk_id)

    if arch_id == "goblin":
        mob.inventory.add_item(ITEMS_DB["hunting_bow"] if random.random() < 0.6 else ITEMS_DB["rusty_sword"])
    elif arch_id == "skeleton":
        mob.inventory.add_item(ITEMS_DB["iron_sword"] if random.random() < 0.5 else ITEMS_DB["fire_staff"])
    else:
        mob.inventory.add_item(ITEMS_DB["potion"] if random.random() < 0.5 else ITEMS_DB["gem"])

    return mob

