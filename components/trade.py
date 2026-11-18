class Trade:
    @staticmethod
    def get_buy_price(buyer_ent, item):
        price = item.value
        if getattr(buyer_ent, "professions", None) and buyer_ent.professions.has_profession("merchant"):
            lvl = buyer_ent.professions.get_level("merchant")
            discount = min(0.35, 0.12 + lvl * 0.03)
            price = max(1, int(price * (1.0 - discount)))
        return price

    @staticmethod
    def get_sell_price(seller_ent, item):
        price = max(1, item.value // 2)
        if getattr(seller_ent, "professions", None) and seller_ent.professions.has_profession("merchant"):
            lvl = seller_ent.professions.get_level("merchant")
            bonus = min(0.50, 0.15 + lvl * 0.05)
            price = max(1, int(price * (1.0 + bonus)))
        return price

    @staticmethod
    def buy_item(buyer_inv, seller_inv, item, buyer_ent=None):
        price = Trade.get_buy_price(buyer_ent, item) if buyer_ent else item.value
        if buyer_inv.gold < price:
            return False, f"Недостаточно золота! Нужно {price}G."
        if len(buyer_inv.items) >= buyer_inv.capacity:
            return False, "В вашем рюкзаке нет места!"

        buyer_inv.gold -= price
        seller_inv.gold += price
        seller_inv.remove_item(item)
        buyer_inv.add_item(item)
        if buyer_ent and getattr(buyer_ent, "professions", None):
            buyer_ent.professions.add_xp("merchant", max(5, price // 4))
        return True, f"Куплено: {item.name} за {price}G"

    @staticmethod
    def sell_item(seller_inv, buyer_inv, item, seller_ent=None):
        sell_price = Trade.get_sell_price(seller_ent, item) if seller_ent else max(1, item.value // 2)
        if buyer_inv.gold < sell_price:
            return False, f"У торговца не хватает золота ({buyer_inv.gold}G)!"
        if len(buyer_inv.items) >= buyer_inv.capacity:
            return False, "У торговца переполнен склад!"

        seller_inv.gold += sell_price
        buyer_inv.gold -= sell_price
        seller_inv.remove_item(item)
        buyer_inv.add_item(item)
        if seller_ent and getattr(seller_ent, "professions", None):
            seller_ent.professions.add_xp("merchant", max(5, sell_price // 3))
        return True, f"Продано: {item.name} за {sell_price}G"
