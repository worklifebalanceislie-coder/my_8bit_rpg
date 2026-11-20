import pygame
import random
from settings import TILE_SIZE

# Каталог мебели по умолчанию (синхронизируется с БД)
DEFAULT_FURNITURE = [
    {"id": "table",     "name": "Деревянный стол / Прилавок", "solid": 1, "interact_kind": None,        "label": ""},
    {"id": "chair",     "name": "Табурет",                    "solid": 0, "interact_kind": None,        "label": ""},
    {"id": "barrel",    "name": "Дубовая бочка",              "solid": 1, "interact_kind": None,        "label": ""},
    {"id": "bookshelf", "name": "Книжный шкаф",               "solid": 1, "interact_kind": None,        "label": ""},
    {"id": "bed",       "name": "Кровать",                    "solid": 1, "interact_kind": "bed",       "label": "Кровать [E — Отдохнуть]"},
    {"id": "anvil",     "name": "Наковальня",                 "solid": 1, "interact_kind": "workbench", "label": "Наковальня [E — Ковать]"},
    {"id": "forge",     "name": "Кузнечный горн / Камин",     "solid": 1, "interact_kind": None,        "label": ""},
    {"id": "weapon_rack","name": "Оружейная стойка",          "solid": 1, "interact_kind": None,        "label": ""},
    {"id": "plant",     "name": "Кадка с растением",          "solid": 1, "interact_kind": None,        "label": ""},
]

_FURNITURE_CACHE = {}

def _add_floor_shadow(surf, x, y, w, h):
    """Рисует полупрозрачную тень на полу под мебелью"""
    shadow = pygame.Surface((w, h), pygame.SRCALPHA)
    shadow.fill((10, 12, 18, 85))
    surf.blit(shadow, (x, y))

def get_furniture_sprite(item_id, connect_left=False, connect_right=False):
    """Возвращает 16x16 Surface мебели с прозрачным фоном и тенью на полу"""
    key = (item_id, connect_left, connect_right)
    if key in _FURNITURE_CACHE:
        return _FURNITURE_CACHE[key]

    s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    outline = (24, 22, 28)

    if item_id == "table":
        # Соединяемый стол / барная стойка (без боковых стенок на стыках)
        x1 = 0 if connect_left else 1
        x2 = 16 if connect_right else 15
        w = x2 - x1
        _add_floor_shadow(s, x1, 12, w, 4)
        # Столешница
        pygame.draw.rect(s, (168, 112, 58), (x1, 3, w, 7))
        pygame.draw.rect(s, (198, 140, 80), (x1 + (0 if connect_left else 1), 4, w - (0 if connect_left else 1) - (0 if connect_right else 1), 3))
        # Передний торец и ножки
        pygame.draw.rect(s, (112, 68, 32), (x1, 10, w, 3))
        if not connect_left:
            pygame.draw.rect(s, (86, 50, 22), (x1 + 1, 13, 2, 2))
            pygame.draw.line(s, outline, (x1, 3), (x1, 14), 1)
        if not connect_right:
            pygame.draw.rect(s, (86, 50, 22), (x2 - 3, 13, 2, 2))
            pygame.draw.line(s, outline, (x2 - 1, 3), (x2 - 1, 14), 1)
        pygame.draw.line(s, outline, (x1, 2), (x2 - 1, 2), 1)
        pygame.draw.line(s, outline, (x1, 10), (x2 - 1, 10), 1)

    elif item_id == "chair":
        _add_floor_shadow(s, 4, 12, 8, 3)
        pygame.draw.rect(s, (135, 86, 42), (5, 7, 6, 4))
        pygame.draw.rect(s, (165, 112, 58), (5, 7, 6, 2))
        pygame.draw.rect(s, (92, 56, 26), (5, 11, 2, 3))
        pygame.draw.rect(s, (92, 56, 26), (9, 11, 2, 3))
        pygame.draw.rect(s, outline, (4, 6, 8, 8), 1)

    elif item_id == "barrel":
        _add_floor_shadow(s, 3, 12, 10, 4)
        # Округлый силуэт бочки без черного квадрата
        pygame.draw.rect(s, (148, 94, 44), (4, 2, 8, 12))
        pygame.draw.rect(s, (175, 116, 60), (5, 3, 4, 10))
        pygame.draw.rect(s, (110, 68, 30), (10, 3, 2, 10))
        # Металлические обручи
        pygame.draw.line(s, (80, 88, 102), (4, 5), (11, 5), 1)
        pygame.draw.line(s, (80, 88, 102), (4, 10), (11, 10), 1)
        # Верхняя крышка
        pygame.draw.rect(s, (124, 76, 34), (5, 2, 6, 2))
        pygame.draw.rect(s, outline, (3, 2, 10, 12), 1)

    elif item_id == "bookshelf":
        _add_floor_shadow(s, 1, 13, 14, 3)
        pygame.draw.rect(s, (118, 72, 36), (1, 0, 14, 15))
        pygame.draw.rect(s, (78, 46, 22), (2, 1, 12, 13))
        for sy in (5, 10):
            pygame.draw.line(s, (135, 86, 44), (2, sy), (13, sy), 1)
        rng = random.Random(42)
        b_cols = [(205, 65, 65), (65, 135, 205), (75, 170, 90), (230, 190, 65), (160, 85, 195)]
        for ry in (2, 7, 11):
            for bx in range(3, 12, 2):
                pygame.draw.rect(s, rng.choice(b_cols), (bx, ry, 2, 3))
        pygame.draw.rect(s, outline, (1, 0, 14, 15), 1)

    elif item_id == "bed":
        _add_floor_shadow(s, 2, 13, 12, 3)
        # Деревянный каркас и подушка
        pygame.draw.rect(s, (124, 74, 36), (2, 1, 12, 14))
        pygame.draw.rect(s, (238, 238, 244), (4, 3, 8, 3))   # Подушка
        pygame.draw.rect(s, (185, 55, 65), (3, 6, 10, 7))    # Одеяло
        pygame.draw.rect(s, (215, 80, 90), (4, 7, 8, 2))     # Отворот одеяла
        pygame.draw.rect(s, outline, (2, 1, 12, 14), 1)

    elif item_id == "anvil":
        # Наковальня на дубовой колоде (прозрачный фон вокруг!)
        _add_floor_shadow(s, 3, 12, 10, 4)
        # Деревянная колода-подставка
        pygame.draw.rect(s, (124, 76, 36), (4, 9, 8, 5))
        pygame.draw.rect(s, outline, (4, 9, 8, 5), 1)
        # Стальная наковальня с рогом
        pygame.draw.rect(s, (145, 155, 172), (2, 5, 11, 3))
        pygame.draw.rect(s, (185, 195, 212), (3, 5, 8, 1))
        pygame.draw.rect(s, (100, 108, 122), (5, 8, 6, 2))
        pygame.draw.line(s, outline, (2, 4), (12, 4), 1)
        pygame.draw.line(s, outline, (2, 8), (12, 8), 1)

    elif item_id == "forge":
        # Каменный горн / камин с дымоходом и открытым огнем
        _add_floor_shadow(s, 1, 13, 14, 3)
        pygame.draw.rect(s, (118, 124, 136), (1, 0, 14, 15))
        pygame.draw.rect(s, (88, 94, 106), (2, 1, 12, 5))
        # Топка с углями и пламенем
        pygame.draw.rect(s, (32, 26, 28), (4, 7, 8, 7))
        pygame.draw.rect(s, (235, 85, 28), (5, 9, 6, 5))
        pygame.draw.rect(s, (252, 212, 65), (6, 10, 4, 3))
        pygame.draw.rect(s, outline, (1, 0, 14, 15), 1)

    elif item_id == "weapon_rack":
        _add_floor_shadow(s, 2, 13, 12, 3)
        pygame.draw.rect(s, (118, 72, 36), (2, 2, 2, 12))
        pygame.draw.rect(s, (118, 72, 36), (12, 2, 2, 12))
        pygame.draw.line(s, (145, 92, 46), (2, 5), (13, 5), 2)
        pygame.draw.line(s, (145, 92, 46), (2, 11), (13, 11), 2)
        # Клинки на стойке
        for wx in (6, 10):
            pygame.draw.line(s, (185, 198, 215), (wx, 3), (wx, 12), 1)
            pygame.draw.line(s, (235, 195, 70), (wx - 1, 10), (wx + 1, 10), 1)

    elif item_id == "plant":
        _add_floor_shadow(s, 4, 12, 8, 4)
        pygame.draw.rect(s, (155, 88, 48), (5, 10, 6, 4))
        pygame.draw.rect(s, outline, (5, 10, 6, 4), 1)
        pygame.draw.circle(s, (58, 152, 68), (8, 7), 4)
        pygame.draw.circle(s, (88, 188, 86), (7, 6), 2)

    _FURNITURE_CACHE[key] = s
    return s
