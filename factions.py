# Заполняются автоматически из таблицы factions_catalog базы данных rpg.db
HOSTILE_PAIRS = set()
FACTION_NAMES_RU = {}

def are_hostile(ent_a, ent_b):
    """Возвращает True, если ent_a считает ent_b врагом (по фракции или личной обиде)"""
    if ent_a is ent_b:
        return False

    if getattr(ent_a, "ai", None) and ent_b in ent_a.ai.personal_enemies:
        return True

    f1 = getattr(ent_a, "faction", "neutral")
    f2 = getattr(ent_b, "faction", "neutral")

    if f1 == f2:
        return False

    return (f1, f2) in HOSTILE_PAIRS or (f2, f1) in HOSTILE_PAIRS
