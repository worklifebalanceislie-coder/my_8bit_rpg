class Trade:
    @staticmethod
    def buy_item(buyer_inv, seller_inv, item):
        """Покупатель забирает предмет у продавца за полную цену"""
        if item not in seller_inv.items:
            return False, "Товара нет в наличии"
        if buyer_inv.gold < item.value:
            return False, "Недостаточно золота"
        if len(buyer_inv.items) >= buyer_inv.capacity:
            return False, "Инвентарь полон"

        buyer_inv.gold -= item.value
        seller_inv.gold += item.value
        seller_inv.transfer_to(buyer_inv, item)
        return True, f"Куплено: {item.name} (-{item.value}G)"

    @staticmethod
    def sell_item(seller_inv, buyer_inv, item):
        """Игрок продает предмет торговцу за 50% стоимости"""
        sell_price = max(1, item.value // 2)
        if item not in seller_inv.items:
            return False, "Нет предмета"
        if buyer_inv.gold < sell_price:
            return False, "У торговца нет золота"
        if len(buyer_inv.items) >= buyer_inv.capacity:
            return False, "У торговца нет места"

        seller_inv.gold += sell_price
        buyer_inv.gold -= sell_price
        seller_inv.transfer_to(buyer_inv, item)
        return True, f"Продано: {item.name} (+{sell_price}G)"
