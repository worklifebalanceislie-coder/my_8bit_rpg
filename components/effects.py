import pygame

# Заполняется автоматически из таблицы effects_catalog базы данных rpg.db
EFFECT_DEFS = {}


class StatusEffect:
    def __init__(self, effect_id, duration, power=1, source=None):
        self.id = effect_id
        self.duration = float(duration)
        self.power = power
        self.source = source
        self.tick_timer = 0.0
        meta = EFFECT_DEFS.get(effect_id, {})
        self.name = meta.get("name", effect_id)
        self.color = tuple(meta.get("color", (255, 255, 255)))
        self.tick_interval = meta.get("tick_interval", 0.0)


class StatusEffects:
    def __init__(self, owner):
        self.owner = owner
        self.active = []

    def apply(self, effect_id, duration, power=1, source=None):
        if effect_id not in EFFECT_DEFS:
            return False

        for eff in self.active:
            if eff.id == effect_id:
                eff.duration = max(eff.duration, float(duration))
                eff.power = max(eff.power, power)
                if source:
                    eff.source = source
                return True

        new_eff = StatusEffect(effect_id, duration, power, source)
        self.active.append(new_eff)
        self.owner.say(f"{new_eff.name}!", 0.9)
        return True

    def remove(self, effect_id):
        self.active = [e for e in self.active if e.id != effect_id]

    def has_effect(self, effect_id):
        return any(e.id == effect_id for e in self.active)

    def get_speed_multiplier(self):
        mult = 1.0
        for eff in self.active:
            meta = EFFECT_DEFS.get(eff.id, {})
            if "speed_mult" in meta:
                mult *= meta["speed_mult"]
        return mult

    def get_def_bonus(self):
        bonus = 0
        for eff in self.active:
            meta = EFFECT_DEFS.get(eff.id, {})
            if "def_bonus" in meta:
                bonus += meta["def_bonus"] * eff.power
        return bonus

    def update(self, dt):
        if not self.active:
            return

        for eff in list(self.active):
            eff.duration -= dt
            if eff.tick_interval > 0 and self.owner.stats and self.owner.stats.hp > 0:
                eff.tick_timer += dt
                if eff.tick_timer >= eff.tick_interval:
                    eff.tick_timer -= eff.tick_interval
                    dmg = max(1, int(eff.power))
                    self.owner.stats.hp = max(0.0, self.owner.stats.hp - dmg)
                    self.owner.hurt_timer = 0.12
                    if eff.source:
                        self.owner.last_attacker = eff.source

            if eff.duration <= 0:
                self.active.remove(eff)

    def draw(self, surface):
        if not self.active:
            return
        pygame.draw.rect(surface, self.active[0].color, self.owner.rect, 1)
        start_x = self.owner.rect.x
        y = self.owner.rect.y - 12
        for idx, eff in enumerate(self.active[:4]):
            pygame.draw.rect(surface, eff.color, (start_x + idx * 4, y, 3, 3))

