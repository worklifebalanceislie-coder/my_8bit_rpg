from items import ITEMS_DB

class Quest:
    def __init__(self, quest_id, title, desc, giver_name, target_type, target_id, required_count, reward_gold=0, reward_xp=0, reward_item=None):
        self.id = quest_id
        self.title = title
        self.desc = desc
        self.giver_name = giver_name
        self.target_type = target_type      # 'kill' (убить врага) или 'collect' (принести предмет)
        self.target_id = target_id          # 'monster' (любой монстр) или item_id (например, 'gem')
        self.required_count = required_count
        self.current_count = 0
        self.reward_gold = reward_gold
        self.reward_xp = reward_xp
        self.reward_item = reward_item      # Ключ из ITEMS_DB (например, 'book_heal')
        self.status = "active"              # 'active', 'ready', 'completed'

    def update_collect_progress(self, inventory):
        if self.target_type != "collect" or self.status == "completed":
            return
        count = sum(1 for item in inventory.items if item.id == self.target_id)
        self.current_count = min(self.required_count, count)
        self.status = "ready" if self.current_count >= self.required_count else "active"


class QuestLog:
    def __init__(self, owner):
        self.owner = owner
        self.quests = []  # Список объектов Quest

    def get_quest(self, quest_id):
        for q in self.quests:
            if q.id == quest_id:
                return q
        return None

    def add_quest(self, quest):
        if self.get_quest(quest.id):
            return False, "Это задание уже взято!"
        if quest.target_type == "collect" and self.owner.inventory:
            quest.update_collect_progress(self.owner.inventory)
        self.quests.append(quest)
        return True, f"Новое задание: {quest.title}"

    def on_enemy_killed(self, victim):
        """Вызывается миром при гибели врага от руки владельца журнала"""
        updated_titles = []
        for q in self.quests:
            if q.status == "active" and q.target_type == "kill":
                if q.target_id == "any" or victim.faction == q.target_id:
                    q.current_count = min(q.required_count, q.current_count + 1)
                    if q.current_count >= q.required_count:
                        q.status = "ready"
                        updated_titles.append(f"Задание выполнено: {q.title}!")
                    else:
                        updated_titles.append(f"{q.title}: {q.current_count}/{q.required_count}")
        return updated_titles

    def refresh_collect_quests(self):
        if not self.owner.inventory:
            return
        for q in self.quests:
            if q.target_type == "collect" and q.status != "completed":
                q.update_collect_progress(self.owner.inventory)

    def complete_quest(self, quest_id):
        q = self.get_quest(quest_id)
        if not q:
            return False, "Задание не найдено"

        self.refresh_collect_quests()
        if q.status != "ready":
            return False, "Условия задания еще не выполнены!"

        # Если нужно было принести предметы — забираем их из рюкзака
        if q.target_type == "collect" and self.owner.inventory:
            removed = 0
            for item in list(self.owner.inventory.items):
                if item.id == q.target_id and removed < q.required_count:
                    self.owner.inventory.remove_item(item)
                    removed += 1

        # Выдаем награду
        if self.owner.inventory and q.reward_gold > 0:
            self.owner.inventory.gold += q.reward_gold
        if q.reward_item and q.reward_item in ITEMS_DB and self.owner.inventory:
            self.owner.inventory.add_item(ITEMS_DB[q.reward_item])
        if self.owner.stats and q.reward_xp > 0:
            self.owner.stats.gain_xp(q.reward_xp)

        q.status = "completed"
        return True, f"Награда получена: +{q.reward_gold}G, +{q.reward_xp} XP!"
