import math
from components.combat import Projectile

class Skill:
    def __init__(self, skill_id, name, kind, mana_cost=0, cooldown=3.0, desc=""):
        self.id = skill_id
        self.name = name
        self.kind = kind          # 'active' или 'passive'
        self.mana_cost = mana_cost
        self.cooldown = cooldown
        self.timer = 0.0
        self.desc = desc

SKILLS_DB = {
    "whirlwind": Skill("whirlwind", "Вихрь клинка", "active", mana_cost=12, cooldown=3.5, desc="Круговой удар. Урон: Сила x2"),
    "volley": Skill("volley", "Залп стрел", "active", mana_cost=14, cooldown=3.0, desc="Веер из 3 стрел. Урон: Ловкость x1.5"),
    "ice_bolt": Skill("ice_bolt", "Ледяная стрела", "active", mana_cost=15, cooldown=2.5, desc="Урон: Инт x2.2 + замедление врага"),
    "heal_spell": Skill("heal_spell", "Свет исцеления", "active", mana_cost=18, cooldown=5.0, desc="Лечит: 15 + Интеллект x3 HP"),
    "passive_blade": Skill("passive_blade", "Мастер клинка", "passive", desc="Пассивно: +50% от Силы к ближ. урону"),
    "passive_skin": Skill("passive_skin", "Каменная кожа", "passive", desc="Пассивно: +50% от Стойкости к броне"),
    "passive_mana": Skill("passive_mana", "Поток маны", "passive", desc="Пассивно: +0.5 x Инт к регену MP/с"),
}

def create_skill(skill_id):
    template = SKILLS_DB.get(skill_id)
    if not template:
        return None
    return Skill(template.id, template.name, template.kind, template.mana_cost, template.cooldown, template.desc)


class SkillBook:
    def __init__(self, owner, max_slots=4):
        self.owner = owner
        self.max_slots = max_slots
        self.learned = []  # Список выученных объектов Skill (макс. 4)

    def has_skill(self, skill_id):
        return any(s.id == skill_id for s in self.learned)

    def learn_skill(self, skill_id):
        if self.has_skill(skill_id):
            return False, "Этот навык уже изучен!"
        if len(self.learned) >= self.max_slots:
            return False, f"Память заполнена ({self.max_slots}/{self.max_slots})! Забудьте навык в меню [K]."
        sk = create_skill(skill_id)
        if sk:
            self.learned.append(sk)
            return True, f"Изучен навык: {sk.name}!"
        return False, "Неизвестный навык"

    def forget_skill(self, index):
        if 0 <= index < len(self.learned):
            removed = self.learned.pop(index)
            return True, f"Забыт навык: {removed.name}"
        return False, ""

    def get_active_skills(self):
        return [s for s in self.learned if s.kind == "active"]

    def update(self, dt):
        for sk in self.learned:
            if sk.timer > 0:
                sk.timer = max(0.0, sk.timer - dt)

    def use_active_slot(self, slot_index, entities, projectiles, walls, aim_pos=None):
        """Применяет активный навык по номеру слота (0 или 1)"""
        actives = self.get_active_skills()
        if slot_index >= len(actives):
            return False, "Слот навыка пуст"

        sk = actives[slot_index]
        st = self.owner.stats
        if not st:
            return False, ""
        if sk.timer > 0:
            return False, f"{sk.name}: перезарядка ({sk.timer:.1f}с)"
        if st.mp < sk.mana_cost:
            self.owner.say("Мало маны!", 0.8)
            return False, "Недостаточно маны!"

        # Направление прицела мыши или направление взгляда персонажа (включая верх/низ)
        if aim_pos:
            ax, ay = aim_pos
            dx = ax - self.owner.rect.centerx
            dy = ay - self.owner.rect.centery
            dist = math.hypot(dx, dy)
            dx, dy = (dx / dist, dy / dist) if dist > 0 else self.owner.facing_dir
            if dx != 0:
                self.owner.facing_left = (dx < 0)
        else:
            dx, dy = getattr(self.owner, "facing_dir", (-1.0 if self.owner.facing_left else 1.0, 0.0))

        # 1. ВИХРЬ КЛИНКА (Круговой удар вокруг себя от Силы)
        if sk.id == "whirlwind":
            st.mp -= sk.mana_cost
            sk.timer = sk.cooldown
            self.owner.say("Вихрь!", 0.8)
            if self.owner.combat:
                self.owner.combat.swing_timer = 0.25
            aoe = self.owner.rect.inflate(34, 34)
            raw_dmg = st.str * 2 + (self.owner.equipment.get_total_bonus("atk") if self.owner.equipment else 0)
            for target in entities:
                if target is self.owner or not target.stats or target.stats.hp <= 0:
                    continue
                if target.faction == self.owner.faction:
                    continue
                if aoe.colliderect(target.rect):
                    dmg, is_crit = st.roll_damage(raw_dmg, target.stats.get_def())
                    target.stats.hp = max(0.0, target.stats.hp - dmg)
                    target.hurt_timer = 0.2
                    target.last_attacker = self.owner
                    if is_crit:
                        target.say("КРИТ!", 0.8)
            return True, f"Применено: {sk.name}"

        # 2. ЗАЛП СТРЕЛ (Веер из 3 стрел от Ловкости)
        elif sk.id == "volley" and projectiles is not None:
            st.mp -= sk.mana_cost
            sk.timer = sk.cooldown
            self.owner.say("Залп!", 0.8)
            dmg = max(2, int(st.agi * 1.5))
            base_angle = math.atan2(dy, dx)
            for offset in (-0.25, 0.0, 0.25):
                ang = base_angle + offset
                adx, ady = math.cos(ang), math.sin(ang)
                p = Projectile(self.owner.rect.centerx + adx * 6, self.owner.rect.centery, adx, ady, self.owner, dmg, "arrow")
                projectiles.append(p)
            return True, f"Применено: {sk.name}"

        # 3. ЛЕДЯНАЯ СТРЕЛА (Урон от Интеллекта + замедление врага)
        elif sk.id == "ice_bolt" and projectiles is not None:
            st.mp -= sk.mana_cost
            sk.timer = sk.cooldown
            self.owner.say("Лед!", 0.8)
            dmg = max(3, int(st.int * 2.2))
            p = Projectile(self.owner.rect.centerx + dx * 6, self.owner.rect.centery, dx, dy, self.owner, dmg, "ice")
            projectiles.append(p)
            return True, f"Применено: {sk.name}"

        # 4. СВЕТ ИСЦЕЛЕНИЯ (Лечение от Интеллекта)
        elif sk.id == "heal_spell":
            st.mp -= sk.mana_cost
            sk.timer = sk.cooldown
            heal_amt = 15 + st.int * 3
            st.hp = min(float(st.max_hp), st.hp + heal_amt)
            self.owner.say(f"+{heal_amt} HP!", 1.0)
            return True, f"Исцеление: +{heal_amt} HP"

        return False, ""
