import random
import math
from components.trade import Trade
from components.pathfinding import find_path
from factions import are_hostile

class AIController:
    def __init__(self, owner, role="merchant", aggro_radius=95):
        self.owner = owner
        self.role = role
        self.aggro_radius = aggro_radius
        self.timer = 0.0
        self.dir_x = 0
        self.dir_y = 0
        self.personal_enemies = set()
        self.trade_cooldown = 0.0
        self.path = []
        self.path_timer = 0.0
        self.path_goal = None
        self.last_pos = None
        self.stuck_timer = 0.0
        self.world = None

    def update(self, dt, world):
        self.world = world
        entities = world.entities
        walls = world.walls

        if self.trade_cooldown > 0:
            self.trade_cooldown -= dt
        if self.path_timer > 0:
            self.path_timer -= dt

        self.manage_gear()
        self.manage_healing()
        self.manage_level_up()
        self.manage_books()

        attacker = self.owner.last_attacker
        if attacker and attacker.stats and attacker.stats.hp > 0:
            if attacker not in self.personal_enemies:
                self.personal_enemies.add(attacker)
                if self.role == "merchant":
                    self.owner.say("Стража! Помогите!")
                    for ent in entities:
                        if ent.ai and ent.ai.role == "guard" and self.distance_to(ent) < 160:
                            ent.ai.personal_enemies.add(attacker)
                            ent.say("Иду на помощь!")
                elif self.role == "guard":
                    self.owner.say("Именем закона!")
                elif self.role == "adventurer":
                    self.owner.say("Зря ты это начал!")

        self.personal_enemies = {e for e in self.personal_enemies if e in entities and e.stats and e.stats.hp > 0}

        if self.role == "merchant":
            self.behave_merchant(dt, walls, entities)
        elif self.role == "guard":
            self.behave_guard(dt, walls, entities)
        elif self.role == "adventurer":
            self.behave_adventurer(dt, walls, entities)
        elif self.role == "monster":
            self.behave_monster(dt, walls, entities)

    def get_item_score(self, item):
        return item.stats_bonus.get("atk", 0) + item.stats_bonus.get("def", 0) + item.stats_bonus.get("capacity", 0)

    def manage_gear(self):
        if self.role == "merchant" or not (self.owner.inventory and self.owner.equipment):
            return
        for item in list(self.owner.inventory.items):
            if item.type in self.owner.equipment.slots:
                current = self.owner.equipment.slots[item.type]
                if current is None or self.get_item_score(item) > self.get_item_score(current):
                    self.owner.equipment.equip(item, self.owner.inventory)

    def manage_healing(self):
        if not (self.owner.stats and self.owner.inventory):
            return
        if self.owner.stats.hp < self.owner.stats.max_hp * 0.45:
            for item in list(self.owner.inventory.items):
                if item.type == "consumable" and "heal" in item.stats_bonus:
                    heal = item.stats_bonus["heal"]
                    self.owner.stats.hp = min(float(self.owner.stats.max_hp), self.owner.stats.hp + heal)
                    self.owner.inventory.remove_item(item)
                    self.owner.say(f"+{heal} HP")
                    break
        if self.owner.stats.mp < 15:
            for item in list(self.owner.inventory.items):
                if item.type == "consumable" and "mana" in item.stats_bonus:
                    mana = item.stats_bonus["mana"]
                    self.owner.stats.mp = min(float(self.owner.stats.max_mp), self.owner.stats.mp + mana)
                    self.owner.inventory.remove_item(item)
                    self.owner.say(f"+{mana} MP")
                    break

    def manage_level_up(self):
        if not self.owner.stats:
            return
        while self.owner.stats.stat_points > 0:
            choice = random.choice(["str", "agi", "int", "vit", "end"])
            self.owner.stats.upgrade_stat(choice)

    def manage_books(self):
        if self.role == "merchant" or not (self.owner.inventory and self.owner.skills):
            return
        for item in list(self.owner.inventory.items):
            if item.type == "book" and item.skill_id:
                ok, _ = self.owner.skills.learn_skill(item.skill_id)
                if ok:
                    self.owner.inventory.remove_item(item)
                    self.owner.say(f"Изучил: {item.name}!")
    def distance_to(self, target):
        return math.hypot(target.rect.centerx - self.owner.rect.centerx, target.rect.centery - self.owner.rect.centery)

    def move_towards(self, target, dt, walls):
        if not self.owner.movement:
            return

        goal_pos = target.rect.center if hasattr(target, "rect") else target
        gx, gy = goal_pos
        ox, oy = self.owner.rect.center
        dist_direct = math.hypot(gx - ox, gy - oy)

        if self.last_pos is not None:
            lx, ly = self.last_pos
            moved = math.hypot(ox - lx, oy - ly)
            self.stuck_timer = (self.stuck_timer + dt) if moved < 0.5 else 0.0
        self.last_pos = (ox, oy)

        if self.stuck_timer > 0.3:
            cell_cx = (ox // 16) * 16 + 8
            cell_cy = (oy // 16) * 16 + 8
            dx, dy = cell_cx - ox, cell_cy - oy
            d = math.hypot(dx, dy)
            if d > 1:
                self.owner.movement.move(dx / d, dy / d, dt, walls)
            self.path = []
            self.stuck_timer = 0.0
            return

        if dist_direct <= 14:
            if dist_direct > 0:
                self.owner.movement.move((gx - ox) / dist_direct, (gy - oy) / dist_direct, dt, walls)
            return

        if self.path_timer <= 0 or not self.path or self.path_goal != goal_pos:
            self.path_timer = 0.25
            self.path_goal = goal_pos
            mw = self.world.width if self.world else 640
            mh = self.world.height if self.world else 400
            self.path = find_path((ox, oy), goal_pos, walls, mw, mh)

        if self.path:
            nx, ny = self.path[0]
            dx, dy = nx - ox, ny - oy
            dist = math.hypot(dx, dy)
            if dist < 4:
                self.path.pop(0)
            elif dist > 0:
                self.owner.movement.move(dx / dist, dy / dist, dt, walls)
        elif dist_direct > 0:
            self.owner.movement.move((gx - ox) / dist_direct, (gy - oy) / dist_direct, dt, walls)

    def flee_from(self, threat, dt, walls):
        if not self.owner.movement:
            return
        dx = self.owner.rect.centerx - threat.rect.centerx
        dy = self.owner.rect.centery - threat.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.owner.movement.move(dx / dist, dy / dist, dt, walls)

    def wander(self, dt, walls):
        if not self.owner.movement:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(1.2, 3.0)
            self.dir_x = random.choice([-1, 0, 0, 1])
            self.dir_y = random.choice([-1, 0, 0, 1])
        self.owner.movement.move(self.dir_x, self.dir_y, dt, walls)

    def engage_enemy(self, enemy, dt, walls):
        dist = self.distance_to(enemy)

        if self.owner.skills and self.world:
            actives = self.owner.skills.get_active_skills()
            for idx, sk in enumerate(actives):
                if sk.timer <= 0 and self.owner.stats.mp >= sk.mana_cost:
                    if sk.id == "heal_spell" and self.owner.stats.hp < self.owner.stats.max_hp * 0.6:
                        self.owner.skills.use_active_slot(idx, self.world)
                        return
                    elif sk.id == "whirlwind" and dist <= 22:
                        self.owner.skills.use_active_slot(idx, self.world)
                        return
                    elif sk.id in ("volley", "ice_bolt") and dist <= 110:
                        self.owner.skills.use_active_slot(idx, self.world, aim_pos=enemy.rect.center)
                        return

        style = self.owner.combat.get_weapon_style() if self.owner.combat else "melee"
        if style in ("bow", "staff"):
            if dist < 45 and self.owner.movement:
                self.flee_from(enemy, dt, walls)
            elif dist > 95 and self.owner.movement:
                self.move_towards(enemy, dt, walls)
            else:
                self.owner.facing_left = (enemy.rect.centerx < self.owner.rect.centerx)
                if self.owner.combat and self.world:
                    self.owner.combat.attack(self.world, aim_pos=enemy.rect.center)
            return

        offset_x = 12 if self.owner.rect.centerx >= enemy.rect.centerx else -12
        target_x = enemy.rect.centerx + offset_x
        target_y = enemy.rect.centery
        dist_to_spot = math.hypot(target_x - self.owner.rect.centerx, target_y - self.owner.rect.centery)

        if dist_to_spot > 5 and self.owner.movement:
            self.move_towards((target_x, target_y), dt, walls)
        else:
            self.owner.facing_left = (enemy.rect.centerx < self.owner.rect.centerx)
            if self.owner.combat and self.world:
                self.owner.combat.attack(self.world)

    def has_junk_to_sell(self):
        if not self.owner.inventory:
            return False
        for item in self.owner.inventory.items:
            if item.type == "misc":
                return True
            if item.type in ("weapon", "armor", "backpack") and self.owner.equipment:
                eq = self.owner.equipment.slots.get(item.type)
                if eq and self.get_item_score(item) <= self.get_item_score(eq):
                    return True
        return False

    def find_desired_purchase(self, merchant):
        if not (merchant.inventory and self.owner.inventory):
            return None
        for item in merchant.inventory.items:
            if item.type in ("weapon", "armor", "backpack") and self.owner.inventory.gold >= item.value:
                eq = self.owner.equipment.slots.get(item.type) if self.owner.equipment else None
                if self.get_item_score(item) > (self.get_item_score(eq) if eq else 0):
                    return item
        if sum(1 for i in self.owner.inventory.items if i.type == "consumable") < 2:
            for item in merchant.inventory.items:
                if item.type == "consumable" and self.owner.inventory.gold >= item.value:
                    return item
        return None

    def interact_with_merchant(self, merchant):
        if self.trade_cooldown > 0:
            return
        self.trade_cooldown = 0.8
        for item in list(self.owner.inventory.items):
            is_junk = (item.type == "misc")
            if item.type in ("weapon", "armor", "backpack") and self.owner.equipment:
                eq = self.owner.equipment.slots.get(item.type)
                if eq and self.get_item_score(item) <= self.get_item_score(eq):
                    is_junk = True
            if is_junk:
                ok, _ = Trade.sell_item(self.owner.inventory, merchant.inventory, item)
                if ok:
                    self.owner.say(f"Продал: {item.name}")
                    return

        item_to_buy = self.find_desired_purchase(merchant)
        if item_to_buy:
            ok, _ = Trade.buy_item(self.owner.inventory, merchant.inventory, item_to_buy)
            if ok:
                self.owner.say(f"Купил: {item_to_buy.name}!")
                self.manage_gear()

    def behave_merchant(self, dt, walls, entities):
        for ent in entities:
            if ent is not self.owner and ent.stats and ent.stats.hp > 0:
                if (ent.faction == "monster" or ent in self.personal_enemies) and self.distance_to(ent) < 75:
                    self.flee_from(ent, dt, walls)
                    return
        self.wander(dt, walls)

    def behave_guard(self, dt, walls, entities):
        for ent in entities:
            if ent.faction == "town" and ent.last_attacker and ent.last_attacker.stats and ent.last_attacker.stats.hp > 0:
                if self.distance_to(ent) < 130 and ent.last_attacker not in self.personal_enemies:
                    self.personal_enemies.add(ent.last_attacker)
                    self.owner.say("Защитить горожан!")
        target = self.find_closest_enemy(entities, 180 if self.personal_enemies else self.aggro_radius, True)
        if target:
            self.engage_enemy(target, dt, walls)
        else:
            self.wander(dt, walls)

    def behave_adventurer(self, dt, walls, entities):
        target = self.find_closest_enemy(entities, 160 if self.personal_enemies else self.aggro_radius, True)
        if target:
            self.engage_enemy(target, dt, walls)
            return

        loot_target = None
        best_dist = 240
        has_space = len(self.owner.inventory.items) < self.owner.inventory.capacity
        for ent in entities:
            if ent.is_container and getattr(ent, "owner_lock", 0) <= 0 and ent.inventory:
                if ent.inventory.gold > 0 or (ent.inventory.items and has_space):
                    d = self.distance_to(ent)
                    if d < best_dist:
                        best_dist, loot_target = d, ent

        if loot_target:
            if self.distance_to(loot_target) > 15:
                self.move_towards(loot_target, dt, walls)
            else:
                if loot_target.inventory.gold > 0:
                    g = loot_target.inventory.gold
                    self.owner.inventory.gold += g
                    loot_target.inventory.gold = 0
                    self.owner.say(f"+{g}G")
                if loot_target.inventory.items and has_space:
                    item = loot_target.inventory.items[0]
                    if loot_target.inventory.transfer_to(self.owner.inventory, item):
                        self.owner.say(f"Взял: {item.name}")
            return

        merchant = next((e for e in entities if e.ai and e.ai.role == "merchant" and e.stats and e.stats.hp > 0), None)
        if merchant and (self.has_junk_to_sell() or self.find_desired_purchase(merchant)):
            if self.distance_to(merchant) > 18:
                self.move_towards(merchant, dt, walls)
            else:
                self.interact_with_merchant(merchant)
            return

        self.wander(dt, walls)

    def behave_monster(self, dt, walls, entities):
        target = self.find_closest_enemy(entities, self.aggro_radius, False)
        if target:
            self.engage_enemy(target, dt, walls)
        else:
            self.wander(dt, walls)

    def find_closest_enemy(self, entities, radius, only_monsters_and_personal=False):
        target, best_dist = None, radius
        for ent in entities:
            if ent is self.owner or not ent.stats or ent.stats.hp <= 0:
                continue
            if are_hostile(self.owner, ent):
                d = self.distance_to(ent)
                if d < best_dist:
                    best_dist, target = d, ent
        return target

