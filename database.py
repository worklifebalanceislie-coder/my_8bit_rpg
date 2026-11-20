import sqlite3
import json
from datetime import datetime
from items import Item, ITEMS_DB
from entities import Entity
from components.movement import Movement
from components.inventory import Inventory
from components.equipment import Equipment
from components.stats import Stats
from components.combat import Combat
from components.ai import AIController
from components.skills import SkillBook, Skill, SKILLS_DB
from components.quests import QuestLog, Quest
from components.effects import EFFECT_DEFS
import os

class DatabaseManager:
    def __init__(self, db_path="rpg.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_tables()
        self.settings = self.load_settings()

    def init_tables(self):
        cur = self.conn.cursor()

        # --- КАТАЛОГИ КОНТЕНТА (ШАБЛОНЫ) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, item_type TEXT NOT NULL,
                value INTEGER NOT NULL, stats_bonus TEXT NOT NULL,
                description TEXT NOT NULL, combat_style TEXT NOT NULL, skill_id TEXT, sprite_key TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sprites_catalog (
                sprite_key TEXT PRIMARY KEY, art_matrix TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS effects_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT NOT NULL,
                tick_interval REAL NOT NULL, speed_mult REAL NOT NULL, def_bonus INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS skills_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
                mana_cost INTEGER NOT NULL, cooldown REAL NOT NULL, desc TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS races_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, faction TEXT NOT NULL,
                speed INTEGER NOT NULL, bonuses TEXT NOT NULL, gold_bonus INTEGER NOT NULL,
                racial_skill TEXT, desc TEXT NOT NULL, relations TEXT NOT NULL, sprite_key TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS classes_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, desc TEXT NOT NULL,
                stats TEXT NOT NULL, gold INTEGER NOT NULL, items TEXT NOT NULL, skill TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS factions_catalog (
                id TEXT PRIMARY KEY,
                name_ru TEXT NOT NULL,
                hostile_to TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS npc_templates (
                id TEXT PRIMARY KEY, location_id TEXT NOT NULL, name TEXT NOT NULL,
                x INTEGER NOT NULL, y INTEGER NOT NULL, color TEXT NOT NULL,
                sprite_key TEXT NOT NULL, faction TEXT NOT NULL, is_container INTEGER NOT NULL,
                role TEXT, speed INTEGER NOT NULL, aggro_radius INTEGER NOT NULL,
                capacity INTEGER NOT NULL, gold INTEGER NOT NULL, stats_json TEXT NOT NULL,
                items_json TEXT NOT NULL, dialogue_json TEXT
            )
        """)

        # --- ДИНАМИЧЕСКИЕ ДАННЫЕ (СОХРАНЕНИЯ И НАСТРОЙКИ) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS save_slots (
                slot_id INTEGER PRIMARY KEY, slot_label TEXT NOT NULL,
                player_name TEXT NOT NULL, player_level INTEGER NOT NULL,
                saved_at TEXT NOT NULL, world_cols INTEGER NOT NULL, world_rows INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_entities (
                uid INTEGER PRIMARY KEY AUTOINCREMENT, slot_id INTEGER NOT NULL,
                is_player INTEGER NOT NULL, name TEXT NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL,
                color TEXT NOT NULL, sprite_key TEXT, is_container INTEGER NOT NULL,
                is_loot_bag INTEGER NOT NULL, faction TEXT NOT NULL, data_json TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS items_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, item_type TEXT NOT NULL,
                value INTEGER NOT NULL, stats_bonus TEXT NOT NULL,
                description TEXT NOT NULL, combat_style TEXT NOT NULL, skill_id TEXT, sprite_key TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS races_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, faction TEXT NOT NULL,
                speed INTEGER NOT NULL, bonuses TEXT NOT NULL, gold_bonus INTEGER NOT NULL,
                racial_skill TEXT, desc TEXT NOT NULL, relations TEXT NOT NULL, sprite_key TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS monster_archetypes (
                id TEXT PRIMARY KEY,
                name_ru TEXT NOT NULL,
                base_hp INTEGER NOT NULL,
                base_atk INTEGER NOT NULL,
                speed INTEGER NOT NULL,
                faction TEXT NOT NULL,
                possible_skills TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS monster_parts (
                id TEXT PRIMARY KEY,
                part_type TEXT NOT NULL,
                archetype TEXT NOT NULL,
                art_matrix TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS professions_catalog (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, desc TEXT NOT NULL, bonus_type TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipes_catalog (
                id TEXT PRIMARY KEY, prof_id TEXT NOT NULL, result_item_id TEXT NOT NULL,
                req_level INTEGER NOT NULL, materials_json TEXT NOT NULL, xp_gain INTEGER NOT NULL
            )
        """)

        cur.execute("CREATE TABLE IF NOT EXISTS game_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.conn.commit()

        try:
            cur.execute("ALTER TABLE skills_catalog ADD COLUMN sprite_key TEXT")
        except Exception:
            pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS furniture_catalog (
                id TEXT PRIMARY KEY,
                name TEXT,
                solid INTEGER,
                interact_kind TEXT,
                label TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS building_interiors (
                building_id TEXT PRIMARY KEY,
                kind TEXT,
                cols INTEGER,
                rows INTEGER,
                floor_tile TEXT,
                props_json TEXT,
                npcs_json TEXT
            )
        """)
        try:
            cur.execute("ALTER TABLE furniture_catalog ADD COLUMN sprite_key TEXT")
        except Exception:
            pass
    
    def sync_all_catalogs(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM professions_catalog")
        if cur.fetchone()["cnt"] == 0 and os.path.exists("default_content.json"):
            self.import_from_json_file("default_content.json")

        self.load_items_to_memory()
        self.load_effects_to_memory()
        self.load_skills_to_memory()
        self.load_factions_to_memory()
        self.sync_professions_catalog()

        from furniture import DEFAULT_FURNITURE
        for f in DEFAULT_FURNITURE:
            cur.execute("INSERT OR IGNORE INTO furniture_catalog VALUES (?, ?, ?, ?, ?, NULL)",
                        (f["id"], f["name"], f["solid"], f["interact_kind"], f["label"]))
        self.conn.commit()

    def import_from_json_file(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            dump = json.load(f)
        cur = self.conn.cursor()
        for table, rows in dump.items():
            if not rows:
                continue
            first_row, *_ = rows
            cols = list(first_row.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            for row in rows:
                cur.execute(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", [row[c] for c in cols])
        self.conn.commit()

    def load_sprites_from_db(self, build_func):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sprites_catalog")
        return {r["sprite_key"]: build_func(json.loads(r["art_matrix"])) for r in cur.fetchall()}

    def load_items_to_memory(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM items_catalog")
        ITEMS_DB.clear()
        for r in cur.fetchall():
            ITEMS_DB[r["id"]] = Item(r["id"], r["name"], r["item_type"], r["value"], json.loads(r["stats_bonus"]),
                                     r["description"], r["combat_style"], r["skill_id"], r["sprite_key"])

    def load_effects_to_memory(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM effects_catalog")
        EFFECT_DEFS.clear()
        for r in cur.fetchall():
            EFFECT_DEFS[r["id"]] = {
                "name": r["name"], "color": json.loads(r["color"]),
                "tick_interval": r["tick_interval"], "speed_mult": r["speed_mult"], "def_bonus": r["def_bonus"]
            }

    def load_skills_to_memory(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM skills_catalog")
        SKILLS_DB.clear()
        for r in cur.fetchall():
            SKILLS_DB[r["id"]] = Skill(r["id"], r["name"], r["kind"], r["mana_cost"], r["cooldown"], r["desc"], r["sprite_key"])

    def load_factions_to_memory(self):
        from factions import FACTION_NAMES_RU, HOSTILE_PAIRS
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM factions_catalog")
        FACTION_NAMES_RU.clear()
        HOSTILE_PAIRS.clear()
        for r in cur.fetchall():
            fid = r["id"]
            FACTION_NAMES_RU[fid] = r["name_ru"]
            for enemy_id in json.loads(r["hostile_to"]):
                HOSTILE_PAIRS.add((fid, enemy_id))
                HOSTILE_PAIRS.add((enemy_id, fid))

    def get_races_from_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM races_catalog")
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["bonuses"] = json.loads(d["bonuses"])
            res.append(d)
        return res

    def get_classes_from_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM classes_catalog")
        res = []
        for r in cur.fetchall():
            d = dict(r)
            d["stats"] = json.loads(d["stats"])
            d["items"] = json.loads(d["items"])
            res.append(d)
        return res

    def get_professions_from_db(self):
        from components.professions import ProfessionInfo
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM professions_catalog")
        return [ProfessionInfo(r["id"], r["name"], r["desc"], r["bonus_type"]) for r in cur.fetchall()]

    def spawn_location_entities(self, location_id, sprites):
        """Создает живые сущности для локации напрямую из таблицы npc_templates БД"""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM npc_templates WHERE location_id = ?", (location_id,))
        entities = []
        for r in cur.fetchall():
            spr = sprites.get(r["sprite_key"])
            ent = Entity(r["name"], r["x"], r["y"], tuple(json.loads(r["color"])), sprite=spr,
                         is_container=bool(r["is_container"]), faction=r["faction"], sprite_bank=sprites)
            ent.sprite_key = r["sprite_key"]

            if r["speed"] > 0:
                ent.movement = Movement(ent, speed=r["speed"])

            ent.inventory = Inventory(capacity=r["capacity"], gold=r["gold"])
            for item_id in json.loads(r["items_json"]):
                if item_id in ITEMS_DB:
                    ent.inventory.add_item(ITEMS_DB[item_id])

            st_data = json.loads(r["stats_json"])
            app_cfg = st_data.get("appearance")
            if not bool(r["is_container"]):
                from appearance import build_character_sprite, generate_random_appearance
                app_cfg = st_data.get("appearance")
                if isinstance(app_cfg, dict):
                    ent.appearance = app_cfg
                else:
                    # Определяем расу по фракции НПС и генерируем ему живую внешность
                    fac_to_race = {"monster": "goblin", "undead": "skeleton"}
                    r_id = fac_to_race.get(r["faction"], "human")
                    ent.appearance = generate_random_appearance(r_id)
                    # Для стражника зададим солидный стеганый кафтан и алый цвет мундира
                    if r["role"] == "guard":
                        ent.appearance["body"] = "heavy_tunic"
                        ent.appearance["cloth_color"] = 2
                ent.sprite = build_character_sprite(ent.appearance)

            if st_data:
                ent.equipment = Equipment()
                ent.stats = Stats(
                    hp=st_data.get("hp", 50), mp=st_data.get("mp", 10),
                    str_val=st_data.get("str", 2), agi_val=st_data.get("agi", 2),
                    int_val=st_data.get("int", 2), vit_val=st_data.get("vit", 2), end_val=st_data.get("end", 0)
                )
                if r["role"] in ("guard", "adventurer", "monster"):
                    ent.combat = Combat(ent, cooldown=0.8 if r["role"] == "monster" else 0.5)
                    ent.skills = SkillBook(ent, max_slots=4)

            if r["role"]:
                ent.ai = AIController(ent, role=r["role"], aggro_radius=r["aggro_radius"])

            if r["dialogue_json"]:
                ent.dialogue = json.loads(r["dialogue_json"])

            ent.link_components()
            entities.append(ent)
        return entities

    def sync_sprites_catalog(self, raw_art_dict, build_func):
        cur = self.conn.cursor()
        for key, matrix in raw_art_dict.items():
            cur.execute("INSERT OR IGNORE INTO sprites_catalog VALUES (?, ?)", (key, json.dumps(matrix)))
        self.conn.commit()

        cur.execute("SELECT * FROM sprites_catalog")
        return {r["sprite_key"]: build_func(json.loads(r["art_matrix"])) for r in cur.fetchall()}

    def load_settings(self):
        defaults = {"autosave_minutes": 3, "show_speech": True, "target_fps": 60}
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM game_settings")
        for r in cur.fetchall():
            if r["key"] in defaults:
                defaults[r["key"]] = json.loads(r["value"])
        return defaults

    def save_settings(self):
        cur = self.conn.cursor()
        for k, v in self.settings.items():
            cur.execute("INSERT OR REPLACE INTO game_settings VALUES (?, ?)", (k, json.dumps(v)))
        self.conn.commit()

    def serialize_entity(self, ent):
        data = {
            "facing_left": ent.facing_left,
            "dialogue": ent.dialogue,
            "movement": {"speed": ent.movement.speed} if ent.movement else None,
            "inventory": {"base_capacity": ent.inventory.base_capacity, "gold": ent.inventory.gold,
                          "items": [i.id for i in ent.inventory.items]} if ent.inventory else None,
            "equipment": {s: (i.id if i else None) for s, i in ent.equipment.slots.items()} if ent.equipment else None,
            "stats": {
                "level": ent.stats.level, "xp": ent.stats.xp, "xp_to_next": ent.stats.xp_to_next,
                "stat_points": ent.stats.stat_points, "str": ent.stats.str, "agi": ent.stats.agi,
                "int": ent.stats.int, "vit": ent.stats.vit, "end": ent.stats.end,
                "base_hp": ent.stats.base_hp, "base_mp": ent.stats.base_mp, "hp": ent.stats.hp, "mp": ent.stats.mp
            } if ent.stats else None,
            "combat": {"cooldown": ent.combat.cooldown, "attack_range": ent.combat.attack_range} if ent.combat else None,
            "ai": {"role": ent.ai.role, "aggro_radius": ent.ai.aggro_radius} if ent.ai else None,
            "skills": {"max_slots": ent.skills.max_slots, "learned": [s.id for s in ent.skills.learned]} if ent.skills else None,
            "quests": [
                {"id": q.id, "title": q.title, "desc": q.desc, "giver_name": q.giver_name,
                 "target_type": q.target_type, "target_id": q.target_id, "required_count": q.required_count,
                 "current_count": q.current_count, "reward_gold": q.reward_gold, "reward_xp": q.reward_xp,
                 "reward_item": q.reward_item, "status": q.status}
                for q in ent.quests.quests
            ] if ent.quests else None,
            "effects": [{"id": e.id, "duration": e.duration, "power": e.power} for e in ent.effects.active] if getattr(ent, "effects", None) else [],
            "professions": ent.professions.learned if getattr(ent, "professions", None) else {},
            "appearance": getattr(ent, "appearance", None),
            "max_active_slots": ent.skills.max_active_slots if getattr(ent, "skills", None) else 2,
            "quick_items": getattr(ent, "quick_items", [None, None, None, None]),
        }
        return json.dumps(data, ensure_ascii=False)

    def deserialize_entity(self, row, sprites):
        spr_key = row["sprite_key"]
        spr = sprites.get(spr_key) if spr_key else None
        if spr is None and row["is_player"] and row["faction"] == "undead":
            from monster_gen import assemble_monster_sprite
            spr = assemble_monster_sprite(["body_ribcage", "head_skull"], (220, 215, 200), (155, 150, 135), (80, 210, 255))

        ent = Entity(row["name"], row["x"], row["y"], tuple(json.loads(row["color"])), sprite=spr,
                     is_container=bool(row["is_container"]), faction=row["faction"], sprite_bank=sprites)
        ent.sprite_key = spr_key
        ent.is_loot_bag = bool(row["is_loot_bag"])

        data = json.loads(row["data_json"])
        ent.facing_left = data.get("facing_left", False)
        ent.dialogue = data.get("dialogue")
        ent.appearance = data.get("appearance")
        if ent.appearance:
            from appearance import build_character_sprite
            ent.sprite = build_character_sprite(ent.appearance)

        if data["movement"]:
            ent.movement = Movement(ent, speed=data["movement"]["speed"])
        if data["inventory"]:
            inv = data["inventory"]
            ent.inventory = Inventory(capacity=inv["base_capacity"], gold=inv["gold"])
            for item_id in inv["items"]:
                if item_id in ITEMS_DB:
                    ent.inventory.add_item(ITEMS_DB[item_id])
        if data["equipment"]:
            ent.equipment = Equipment()
            for slot, item_id in data["equipment"].items():
                if item_id and item_id in ITEMS_DB:
                    ent.equipment.slots[slot] = ITEMS_DB[item_id]
        if data["stats"]:
            st = data["stats"]
            ent.stats = Stats(st["base_hp"], st["base_mp"], st["str"], st["agi"], st["int"], st["vit"], st["end"])
            ent.stats.level, ent.stats.xp, ent.stats.xp_to_next, ent.stats.stat_points = st["level"], st["xp"], st["xp_to_next"], st["stat_points"]
            ent.stats.hp, ent.stats.mp = st["hp"], st["mp"]
        if data["combat"]:
            ent.combat = Combat(ent, cooldown=data["combat"]["cooldown"], attack_range=data["combat"]["attack_range"])
        if data["ai"]:
            ent.ai = AIController(ent, role=data["ai"]["role"], aggro_radius=data["ai"]["aggro_radius"])
        if data["skills"]:
            ent.skills = SkillBook(ent, max_slots=data["skills"]["max_slots"])
            for sk_id in data["skills"]["learned"]:
                ent.skills.learn_skill(sk_id)
        if data["quests"] is not None:
            ent.quests = QuestLog(ent)
            for qd in data["quests"]:
                q = Quest(qd["id"], qd["title"], qd["desc"], qd["giver_name"], qd["target_type"], qd["target_id"],
                          qd["required_count"], qd["reward_gold"], qd["reward_xp"], qd["reward_item"])
                q.current_count, q.status = qd["current_count"], qd["status"]
                ent.quests.quests.append(q)
        for eff_data in data.get("effects", []):
            ent.effects.apply(eff_data["id"], eff_data["duration"], eff_data["power"])

        if getattr(ent, "professions", None) and data.get("professions"):
            ent.professions.learned = data["professions"]
        
        if getattr(ent, "skills", None):
            ent.skills.max_active_slots = data.get("max_active_slots", 2)
        if "quick_items" in data:
            ent.quick_items = data["quick_items"]

        ent.link_components()
        return ent

    def get_all_saves(self, manual_only=False):
        cur = self.conn.cursor()
        sql = "SELECT * FROM save_slots WHERE slot_id >= 1 AND slot_id < 90 ORDER BY slot_id ASC" if manual_only else "SELECT * FROM save_slots ORDER BY slot_id ASC"
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]

    def get_next_manual_slot_id(self):
        cur = self.conn.cursor()
        cur.execute("SELECT MAX(slot_id) as max_id FROM save_slots WHERE slot_id >= 1 AND slot_id < 90")
        row = cur.fetchone()
        return (row["max_id"] + 1) if (row and row["max_id"] is not None) else 1

    def save_world(self, world, player, sprites, slot_id=None, slot_type="manual"):
        if slot_type == "quick":
            slot_id, label = 0, "Быстрое сохранение"
        elif slot_type == "auto":
            slot_id, label = 99, "Автосохранение"
        else:
            if slot_id is None:
                slot_id = self.get_next_manual_slot_id()
            label = f"Сейв #{slot_id}"

        now_str = datetime.now().strftime("%d.%m %H:%M:%S")
        cur = self.conn.cursor()
        cur.execute("DELETE FROM save_slots WHERE slot_id = ?", (slot_id,))
        cur.execute("DELETE FROM saved_entities WHERE slot_id = ?", (slot_id,))
        cur.execute("INSERT INTO save_slots VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (slot_id, label, player.name, player.stats.level, now_str, world.cols, world.rows))

        reverse_sprites = {v: k for k, v in sprites.items()}
        for ent in world.entities:
            spr_key = getattr(ent, "sprite_key", None) or reverse_sprites.get(ent.sprite)
            cur.execute("INSERT INTO saved_entities (slot_id, is_player, name, x, y, color, sprite_key, is_container, is_loot_bag, faction, data_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (slot_id, 1 if ent is player else 0, ent.name, ent.rect.x, ent.rect.y, json.dumps(list(ent.color)),
                         spr_key, 1 if ent.is_container else 0, 1 if getattr(ent, "is_loot_bag", False) else 0,
                         ent.faction, self.serialize_entity(ent)))
        self.conn.commit()
        return True, f"Сохранено: {label} ({now_str})"

    def load_world(self, sprites, slot_id):
        from world import WorldMap
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM save_slots WHERE slot_id = ?", (slot_id,))
        slot_row = cur.fetchone()
        if not slot_row:
            return None, None, "Слот сохранения пуст!"

        world = WorldMap(cols=slot_row["world_cols"], rows=slot_row["world_rows"])
        cur.execute("SELECT * FROM saved_entities WHERE slot_id = ?", (slot_id,))
        player, loaded_entities = None, []
        for r in cur.fetchall():
            ent = self.deserialize_entity(r, sprites)
            if r["is_player"]:
                player = ent
            loaded_entities.append(ent)

        world.entities = loaded_entities
        return world, player, f"Загружено: {slot_row['slot_label']} ({player.name})"

    def sync_factions_catalog(self):
        from factions import FACTION_NAMES_RU, HOSTILE_PAIRS
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM factions_catalog")
        if cur.fetchone()["cnt"] == 0:
            seeds = [
                ("player", "Вольные герои", ["monster", "undead"]),
                ("town", "Имперский город", ["monster", "undead"]),
                ("free_city", "Вольный город (Нейтралы)", []),
                ("adventurer", "Гильдия странников", ["monster", "undead"]),
                ("monster", "Клан Гоблинов", ["player", "town", "adventurer", "undead"]),
                ("undead", "Легион Нежити", ["player", "town", "adventurer", "monster"]),
            ]
            for fid, fname, enemies in seeds:
                cur.execute("INSERT INTO factions_catalog VALUES (?, ?, ?)", (fid, fname, json.dumps(enemies)))
            self.conn.commit()

        cur.execute("SELECT * FROM factions_catalog")
        FACTION_NAMES_RU.clear()
        HOSTILE_PAIRS.clear()
        for r in cur.fetchall():
            fid = r["id"]
            FACTION_NAMES_RU[fid] = r["name_ru"]
            for enemy_id in json.loads(r["hostile_to"]):
                HOSTILE_PAIRS.add((fid, enemy_id))
                HOSTILE_PAIRS.add((enemy_id, fid))

    def sync_monsters_catalog(self):
        cur = self.conn.cursor()

        cur.execute("SELECT COUNT(*) as cnt FROM monster_archetypes")
        if cur.fetchone()["cnt"] == 0:
            archetypes = [
                ("goblin", "Гоблин", 30, 3, 45, "monster", ["volley", "whirlwind", "passive_blade"]),
                ("skeleton", "Скелет", 35, 4, 42, "undead", ["ice_bolt", "heal_spell", "passive_mana", "passive_blade"]),
                ("slime", "Слизень", 42, 2, 35, "monster", ["passive_skin", "passive_mana", "heal_spell"]),
            ]
            for aid, aname, hp, atk, spd, fac, sks in archetypes:
                cur.execute("INSERT INTO monster_archetypes VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (aid, aname, hp, atk, spd, fac, json.dumps(sks)))

        builtin_parts = [
            ("body_goblin", "body", "goblin", [
                "................",
                "................",
                "................",
                "................",
                "................",
                ".....KKKKKK.....",
                "....KMMMMMMK....",
                "...KmMMMMMMmK...",
                "..KMKMMMMMMKMK..",
                "..KK.LLLLLL.KK..",
                "....KLLLLLLK....",
                "....KLL..LLK....",
                "....Kmm..mmK....",
                "...Kmmm..mmmK...",
                "...KKKK..KKKK...",
                "................"
            ]),
            ("head_goblin_hood", "head", "goblin", [
                ".....KKKKKK.....",
                "....KMMMMMMK....",
                "..KKKMMMMMMKKK..",
                ".KmmMMEMMEMMmmK.",
                "..KKKMMMMMMKKK..",
                "....KmMMMMmK....",
                ".....KKKKKK.....",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................"
            ]),
            ("head_goblin_mohawk", "head", "goblin", [
                "......KKKK......",
                ".....KRRRRK.....",
                "....KMMMMMMK....",
                "..KKKMMMMMMKKK..",
                ".KmmMMEMMEMMmmK.",
                "....KmMMMMmK....",
                ".....KKKKKK.....",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................"
            ]),
            ("body_ribcage", "body", "skeleton", [
                "................",
                "................",
                "................",
                "................",
                "................",
                ".....KKKKKK.....",
                "....KMMMMMMK....",
                "...KMKmMMmKMK...",
                "..KMK.MMMM.KMK..",
                "..KK.KmMMmK.KK..",
                "....KMMMMMMK....",
                "....KMM..MMK....",
                "....Kmm..mmK....",
                "...KMMM..MMMK...",
                "...KKKK..KKKK...",
                "................"
            ]),
            ("head_skull", "head", "skeleton", [
                ".....KKKKKK.....",
                "....KMMMMMMK....",
                "...KMMMMMMMMK...",
                "...KMMEmmEMMK...",
                "....KMMMMMMK....",
                "....KMmMmMmK....",
                ".....KKKKKK.....",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................"
            ]),
            ("head_skull_horns", "head", "skeleton", [
                "..KK........KK..",
                ".KYYKKKKKKKKYYK.",
                "..KYMMMMMMMMYK..",
                "...KMMEmmEMMK...",
                "....KMMMMMMK....",
                "....KMmMmMmK....",
                ".....KKKKKK.....",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................",
                "................"
            ]),
            ("body_slime", "body", "slime", [
                "................",
                "................",
                "................",
                "......KKKK......",
                "....KKMMMMKK....",
                "...KMMMMMMMMK...",
                "..KMMMMMMMMMMK..",
                ".KMMEMMMMMMEMMK.",
                ".KMMMMMMMMMMMMK.",
                "KMMMMMMMMMMMMMMK",
                "KmMMMMMMMMMMMMmK",
                "KmmMMMMMMMMMMmmK",
                ".KmmmmmmmmmmmmK.",
                "..KKKKKKKKKKKK..",
                "................",
                "................"
            ])
        ]
        # Добавляем базовые детали только если их ещё нет в БД (не затираем пользовательские!)
        for pid, ptype, arch, mat in builtin_parts:
            cur.execute("INSERT OR IGNORE INTO monster_parts VALUES (?, ?, ?, ?)",
                        (pid, ptype, arch, json.dumps(mat)))

        self.conn.commit()

    def sync_professions_catalog(self):
        from components.professions import PROFESSIONS_DB, RECIPES_DB, ProfessionInfo, Recipe
        cur = self.conn.cursor()

        cur.execute("SELECT * FROM professions_catalog")
        PROFESSIONS_DB.clear()
        for r in cur.fetchall():
            PROFESSIONS_DB[r["id"]] = ProfessionInfo(r["id"], r["name"], r["desc"], r["bonus_type"])

        cur.execute("SELECT * FROM recipes_catalog")
        RECIPES_DB.clear()
        for r in cur.fetchall():
            RECIPES_DB[r["id"]] = Recipe(
                r["id"], r["prof_id"], r["result_item_id"],
                r["req_level"], json.loads(r["materials_json"]), r["xp_gain"]
            )

    def get_building_interior(self, building_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM building_interiors WHERE building_id = ?", (building_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def save_building_interior(self, building_id, kind, cols, rows, floor_tile, props_list, npcs_list):
        self.conn.execute(
            "INSERT OR REPLACE INTO building_interiors VALUES (?, ?, ?, ?, ?, ?, ?)",
            (building_id, kind, cols, rows, floor_tile,
             json.dumps(props_list, ensure_ascii=False),
             json.dumps(npcs_list, ensure_ascii=False))
        )
        self.conn.commit()
