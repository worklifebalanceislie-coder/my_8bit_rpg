import random

class Stats:
    def __init__(self, hp=60, mp=30, str_val=4, agi_val=3, int_val=3, vit_val=3, end_val=1):
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.stat_points = 0

        # 5 базовых атрибутов
        self.str = str_val   # Сила (ближний бой)
        self.agi = agi_val   # Ловкость (луки + шанс крита)
        self.int = int_val   # Интеллект (магия + мана + реген маны)
        self.vit = vit_val   # Живучесть (HP + реген HP)
        self.end = end_val   # Стойкость (защита)

        self.base_hp = hp
        self.base_mp = mp
        self.equipment = None
        self.skills = None
        self.hp = float(self.max_hp)
        self.mp = float(self.max_mp)

    @property
    def max_hp(self):
        bonus = self.equipment.get_total_bonus("hp") if self.equipment else 0
        return self.base_hp + self.vit * 10 + bonus

    @property
    def max_mp(self):
        bonus = self.equipment.get_total_bonus("mp") if self.equipment else 0
        return self.base_mp + self.int * 10 + bonus

    @property
    def hp_regen(self):
        return round(0.3 + self.vit * 0.35, 1)

    @property
    def mp_regen(self):
        base = 0.8 + self.int * 0.5
        if self.skills and self.skills.has_skill("passive_mana"):
            base += self.int * 0.5
        return round(base, 1)


    @property
    def crit_chance(self):
        return min(50, self.agi * 3)  # В процентах (макс 50%)

    def get_atk(self, style="melee"):
        weapon_bonus = self.equipment.get_total_bonus("atk") if self.equipment else 0
        if style == "bow":
            stat_bonus = self.agi
        elif style == "staff":
            stat_bonus = self.int
        else:
            stat_bonus = self.str
            if self.skills and self.skills.has_skill("passive_blade"):
                stat_bonus += self.str // 2
        return stat_bonus + weapon_bonus


    def get_def(self):
        bonus = self.equipment.get_total_bonus("def") if self.equipment else 0
        total = self.end + bonus
        if self.skills and self.skills.has_skill("passive_skin"):
            total += self.end // 2
        return total


    def roll_damage(self, raw_atk, target_def):
        """Считает итоговый урон с учетом брони и шанса критического удара"""
        dmg = max(1, raw_atk - target_def)
        is_crit = (random.randint(1, 100) <= self.crit_chance)
        if is_crit:
            dmg = max(2, int(dmg * 1.5))
        return dmg, is_crit

    def update(self, dt):
        """Пассивная регенерация здоровья и маны каждую секунду"""
        if self.hp > 0 and self.hp < self.max_hp:
            self.hp = min(float(self.max_hp), self.hp + self.hp_regen * dt)
        if self.mp < self.max_mp:
            self.mp = min(float(self.max_mp), self.mp + self.mp_regen * dt)

    def gain_xp(self, amount):
        leveled_up = False
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.level_up()
            leveled_up = True
        return leveled_up

    def level_up(self):
        self.xp -= self.xp_to_next
        self.level += 1
        self.xp_to_next = int(self.xp_to_next * 1.5)
        self.stat_points += 3
        self.hp = float(self.max_hp)
        self.mp = float(self.max_mp)

    def upgrade_stat(self, stat_name):
        if self.stat_points <= 0:
            return False
        if stat_name == "str":
            self.str += 1
        elif stat_name == "agi":
            self.agi += 1
        elif stat_name == "int":
            self.int += 1
            self.mp = min(float(self.max_mp), self.mp + 10)
        elif stat_name == "vit":
            self.vit += 1
            self.hp = min(float(self.max_hp), self.hp + 10)
        elif stat_name == "end":
            self.end += 1
        else:
            return False
        self.stat_points -= 1
        return True
