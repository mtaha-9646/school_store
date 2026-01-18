from models import db, Item, InventoryLog

def adjust_stock(item_id, delta_qty, event_type, ref_type=None, ref_id=None, note=None, user_id=None):
    """
    Central function to modify stock. 
    Updates Item.stock_on_hand and creates an InventoryLog entry.
    """
    item = Item.query.get(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")

    item.stock_on_hand += delta_qty
    
    log = InventoryLog(
        item_id=item_id,
        event_type=event_type,
        delta_qty=delta_qty,
        ref_type=ref_type,
        ref_id=ref_id,
        note=note,
        user_id=user_id
    )
    db.session.add(log)
    return item
