import pygame

PALETTE = {
    '.': None,
    'D': (115, 85, 55),      # Земля (основа)
    'd': (95, 68, 42),       # Земля (камешки)
    'P': (225, 200, 130),    # Песок (основа)
    'p': (200, 175, 105),    # Песок (рябь)
    'V': (55, 145, 70),      # Трава (основа)
    'v': (42, 118, 55),      # Трава (тень)
    'Z': (85, 175, 90),      # Трава (светлые травинки)
    'A': (65, 130, 215),     # Вода (основа)
    'a': (120, 185, 245),    # Вода (блики)
    'Q': (130, 135, 145),    # Брусчатка (камень)
    'q': (95, 100, 110),     # Брусчатка (швы)
    'K': (20, 20, 28),
    'S': (245, 195, 150),
    'H': (110, 60, 35),
    'G': (70, 180, 100),
    'g': (45, 130, 70),
    'Y': (220, 170, 50),
    'y': (170, 120, 30),
    'B': (150, 90, 50),
    'b': (100, 55, 30),
    'W': (85, 92, 110),
    'w': (60, 65, 80),
    'L': (115, 122, 140),
    'F': (38, 43, 54),
    'f': (46, 52, 64),
    'E': (100, 170, 60),
    'e': (65, 115, 40),
    'R': (220, 50, 50),
    'C': (70, 130, 210),
    'c': (45, 85, 150),
    'M': (195, 205, 220),    # Блестящая сталь (железный меч, кольчуга)
    'm': (130, 140, 155),    # Тень стали
    'U': (190, 55, 55),
    'O': (165, 95, 55),      # Ржавчина (ржавый меч)
    'o': (115, 65, 35),      # Тень ржавчины
}

def build_sprite(matrix):
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    for y, row in enumerate(matrix):
        for x, char in enumerate(row):
            color = PALETTE.get(char)
            if color:
                surf.set_at((x, y), color)
    return surf

PLAYER_ART = [
    ".....KKKKKK.....",
    "....KHHHHHHK....",
    "....KHHHHHHK....",
    "....KSSSSSSK....",
    "....KSKSSKSK....",
    "....KSSSSSSK....",
    ".....KKKKKK.....",
    "...KKGGGGGGKK...",
    "..KGGGGGGGGGGK..",
    "..KGGgGGGGgGGK..",
    "..KSSKGGGGKSSK..",
    "..KK.KYYYYK.KK..",
    ".....KggggK.....",
    ".....KggggK.....",
    ".....KK..KK.....",
    "....KKK..KKK...."
]

NPC_ART = [
    "....KKKKKKKK....",
    "...KYYYYYYYYK...",
    "..KYYYYYYYYYYK..",
    "....KSSSSSSK....",
    "....KSKSSKSK....",
    "....KHHHHHHK....",
    ".....KHHHHK.....",
    "...KKYYYYYYKK...",
    "..KYYyYYYYyYYK..",
    "..KYYyYYYYyYYK..",
    "..KSSKYYYYKSSK..",
    "..KK.KbbbbK.KK..",
    ".....KyyyyK.....",
    ".....KyyyyK.....",
    ".....KK..KK.....",
    "....KKK..KKK...."
]

GOBLIN_ART = [
    "................",
    "....KKKKKKKK....",
    "..KKKEEEEEEKKK..",
    ".KEEKREEEERKKEK.",
    "..KKKEEEEEEKKK..",
    "....KEKKKKKK....",
    ".....KKKKKK.....",
    "...KKbbbbbbKK...",
    "..KbbbbbbbbbbK..",
    "..KEEKbbbbKEEK..",
    "..KK.KYYYYK.KK..",
    ".....KeeeeK.....",
    ".....KeeeeK.....",
    ".....KK..KK.....",
    "....KKK..KKK....",
    "................"
]

GUARD_ART = [
    "....KKKKKKKK....",
    "...KMMMMMMMMK...",
    "..KMMmMMMMmMMK..",
    "...KMSSSSSSMK...",
    "....KSKSSKSK....",
    "....KSSSSSSK....",
    ".....KKKKKK.....",
    "...KKUUUUUUKK...",
    "..KUUUUUUUUUUK..",
    "..KUUYUUUUYUUK..",
    "..KMMKUUUUKMMK..",
    "..KK.KMMMMK.KK..",
    ".....KmmmmK.....",
    ".....KmmmmK.....",
    ".....KK..KK.....",
    "....KKK..KKK...."
]

ADVENTURER_ART = [
    ".....KKKKKK.....",
    "....KYYYYYYK....",
    "....KYYYYYYK....",
    "....KSSSSSSK....",
    "....KSKSSKSK....",
    "....KSSSSSSK....",
    ".....KKKKKK.....",
    "...KKCCCCCCKK...",
    "..KCCCCCCCCCCK..",
    "..KCCcCCCCcCCK..",
    "..KSSKCCCCKSSK..",
    "..KK.KbbbbK.KK..",
    ".....KccccK.....",
    ".....KccccK.....",
    ".....KK..KK.....",
    "....KKK..KKK...."
]

# --- СЛОИ ЭКИПИРОВКИ (накладываются поверх персонажа) ---

LEATHER_ARMOR_ART = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "....KKKKKKKK....",
    "....KBBBBBBK....",
    "....KBbBBbBK....",
    ".....KBBBBK.....",
    ".....KYYYYK.....",
    "................",
    "................",
    "................",
    "................"
]

CHAINMAIL_ART = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "....KKKKKKKK....",
    "....KMmMmMmK....",
    "....KmMmMmMK....",
    ".....KMmMmK.....",
    ".....KYYYYK.....",
    "................",
    "................",
    "................",
    "................"
]

RUSTY_SWORD_ART = [
    "................",
    "................",
    "................",
    "..............K.",
    ".............KOK",
    "............KOoK",
    "...........KOoK.",
    "..........KOoK..",
    ".........KKYK...",
    "........KYYK....",
    "........KHK.....",
    "................",
    "................",
    "................",
    "................",
    "................"
]

IRON_SWORD_ART = [
    "................",
    "................",
    "...............K",
    "..............KM",
    ".............KMM",
    "............KMMm",
    "...........KMMmK",
    "..........KMMmK.",
    ".........KKYK...",
    "........KYYK....",
    "........KHK.....",
    "................",
    "................",
    "................",
    "................",
    "................"
]

BOW_ART = [
    "................",
    "................",
    "................",
    "...........KK...",
    "..........KBBK..",
    ".........KB..MK.",
    ".........KB..MK.",
    ".........KB..MK.",
    ".........KB..MK.",
    "..........KBBK..",
    "...........KK...",
    "................",
    "................",
    "................",
    "................",
    "................"
]

FIRE_STAFF_ART = [
    "................",
    "............KK..",
    "...........KRRK.",
    "...........KYYK.",
    "............KK..",
    "............KB..",
    "...........KB...",
    "..........KB....",
    ".........KB.....",
    "........KB......",
    ".......KB.......",
    "................",
    "................",
    "................",
    "................",
    "................"
]

LOOT_ART = [
    "................",
    "................",
    "......KKKK......",
    ".....KBBBBK.....",
    "......KYYK......",
    "....KKBBBBKK....",
    "...KBBBBBBBBK...",
    "..KBBBBbbBBBBK..",
    "..KBBBbbbbBBBK..",
    "..KBBBBbbBBBBK..",
    "...KbbbbbbbbK...",
    "....KKKKKKKK....",
    "................",
    "................",
    "................",
    "................"
]

CHEST_ART = [
    "................",
    "................",
    "..KKKKKKKKKKKK..",
    ".KBBBBBBBBBBBBK.",
    ".KBBBBYYYYBBBBK.",
    ".KBBBBYKKYBBBBK.",
    ".KKKKKKKKKKKKKK.",
    ".KbbbbYKKYbbbbK.",
    ".KbbbbYYYYbbbbK.",
    ".KbbbbbbbbbbbbK.",
    ".KbbbbbbbbbbbbK.",
    ".KbbbbbbbbbbbbK.",
    "..KKKKKKKKKKKK..",
    "................",
    "................",
    "................"
]

WALL_ART = [
    "LLLLLLLLLLLLLLLw",
    "LWWWWWWwWWWWWWWw",
    "LWWWWWWwWWWWWWWw",
    "wwwwwwwwwwwwwwww",
    "LLLwLLLLLLLLLLLw",
    "WWWwWWWWWWWWWWWw",
    "WWWwWWWWWWWWWWWw",
    "wwwwwwwwwwwwwwww",
    "LLLLLLLLLLwLLLLw",
    "WWWWWWWWWWwWWWWw",
    "WWWWWWWWWWwWWWWw",
    "wwwwwwwwwwwwwwww",
    "LLLLwLLLLLLLLLLw",
    "WWWWwWWWWWWWWWWw",
    "WWWWwWWWWWWWWWWw",
    "wwwwwwwwwwwwwwww"
]

FLOOR_ART = [
    "FFFFFFFFFFFFFFFF",
    "FffFFFFFFFFFFFFF",
    "FffFFFFFFFFFFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFFFFFFFffFFFF",
    "FFFFFFFFFFffFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFffFFFFFFFFFF",
    "FFFFffFFFFFFFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFFFFFFFFFFFFF",
    "FFFFFFFFFFFFffFF",
    "FFFFFFFFFFFFffFF",
    "FFFFFFFFFFFFFFFF"
]

GRASS_ART = [
    "VVVVVVVVVVVVVVVV",
    "VVZVVVVVVVVVVVVV",
    "VVVVVVVVVVvVVVVV",
    "VVVVVVVVVVVVVVVV",
    "VVVVVVVVVVVVZVVV",
    "VVvVVVVVVVVVVVVV",
    "VVVVVVVVVVVVVVVV",
    "VVVVVVZVVVVVVVVV",
    "VVVVVVVVVVVVVVvV",
    "VVVVVVVVVVVVVVVV",
    "VVZVVVVVVVVVVVVV",
    "VVVVVVVVVvVVVVVV",
    "VVVVVVVVVVVVVVVV",
    "VVVVVVVVVVVVZVVV",
    "VVVVvVVVVVVVVVVV",
    "VVVVVVVVVVVVVVVV"
]

DIRT_ART = [
    "DDDDDDDDDDDDDDDD",
    "DDdDDDDDDDDDDDDD",
    "DDDDDDDDDDDdDDDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDdDDDDDDDDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDDDDDdDDD",
    "DDdDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDdDDDDDDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDdDDDDDDDDdDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDDDdDDDDD",
    "DDdDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDD"
]

SAND_ART = [
    "PPPPPPPPPPPPPPPP",
    "PPpPPPPPPPPPPPPP",
    "PPPPPPPPPPpPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPpPPPPPPPPPPP",
    "PPPPPPPPPPPPpPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPpPPPPPPP",
    "PPpPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPpPPP",
    "PPPPPPpPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPpPPPPPPPPPPPPP",
    "PPPPPPPPpPPPPPPP",
    "PPPPPPPPPPPPPPPP"
]

COBBLE_ART = [
    "qqqqqqqqqqqqqqqq",
    "qQQQQQqQQQQQQQqQ",
    "qQQQQQqQQQQQQQqQ",
    "qQQQQQqQQQQQQQqQ",
    "qqqqqqqqqqqqqqqq",
    "QQQqQQQQQQQqQQQQ",
    "QQQqQQQQQQQqQQQQ",
    "QQQqQQQQQQQqQQQQ",
    "qqqqqqqqqqqqqqqq",
    "qQQQQQqQQQQQQQqQ",
    "qQQQQQqQQQQQQQqQ",
    "qQQQQQqQQQQQQQqQ",
    "qqqqqqqqqqqqqqqq",
    "QQQqQQQQQQQqQQQQ",
    "QQQqQQQQQQQqQQQQ",
    "qqqqqqqqqqqqqqqq"
]

WATER_ART = [
    "AAAAAAAAAAAAAAAA",
    "AAaaAAAAAAAAAAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAAAAAAAaaaAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAaaaAAAAAAAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAAAAAAAAAaaAA",
    "AAAAAAAAAAAAAAAA",
    "AAaaaAAAAAAAAAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAAAAAaaAAAAAA",
    "AAAAAAAAAAAAAAAA",
    "AAAAaaAAAAAAAAAA",
    "AAAAAAAAAAAAAAAA"
]

def load_sprites():
    return {
        "player": build_sprite(PLAYER_ART),
        "npc": build_sprite(NPC_ART),
        "goblin": build_sprite(GOBLIN_ART),
        "guard": build_sprite(GUARD_ART),
        "adventurer": build_sprite(ADVENTURER_ART),
        "loot": build_sprite(LOOT_ART),
        "chest": build_sprite(CHEST_ART),
        "wall": build_sprite(WALL_ART),
        "floor": build_sprite(FLOOR_ART),
        # Спрайты экипировки по item_id
        "equip_leather_armor": build_sprite(LEATHER_ARMOR_ART),
        "equip_chainmail": build_sprite(CHAINMAIL_ART),
        "equip_rusty_sword": build_sprite(RUSTY_SWORD_ART),
        "equip_iron_sword": build_sprite(IRON_SWORD_ART),
        "equip_hunting_bow": build_sprite(BOW_ART),
        "equip_fire_staff": build_sprite(FIRE_STAFF_ART),
        "grass": build_sprite(GRASS_ART),
        "dirt": build_sprite(DIRT_ART),
        "sand": build_sprite(SAND_ART),
        "cobble": build_sprite(COBBLE_ART),
        "water": build_sprite(WATER_ART),

    }
