from models import db, Item, Transaction, TransactionLine
from services.inventory import adjust_stock
from services.signatures import save_signature

def process_checkout(user_id, teacher_id, cart_items, signature_data, instance_path):
    """
    Process the checkout transaction atomically.
    cart_items: dict of {item_id: qty}
    """
    if not cart_items:
        raise ValueError("Cart is empty")
    
    if not signature_data:
        raise ValueError("Signature is required")

    try:
        # Calculate totals and validate stock FIRST
        total_cents = 0
        line_items_data = []

        for item_id, qty in cart_items.items():
            qty = int(qty)
            if qty <= 0:
                continue
            
            item = Item.query.get(item_id)
            if not item:
                raise ValueError(f"Item {item_id} not found")
            
            # Stock check
            if item.stock_on_hand < qty:
                raise ValueError(f"Not enough stock for {item.name}. Have {item.stock_on_hand}, need {qty}")

            line_total = item.price_cents * qty
            total_cents += line_total
            line_items_data.append({
                'item': item,
                'qty': qty,
                'price': item.price_cents
            })

        # Save signature
        sig_path = save_signature(signature_data, instance_path)

        # Create Transaction
        transaction = Transaction(
            teacher_id=teacher_id,
            user_id=user_id,
            total_cents=total_cents,
            signature_path=sig_path
        )
        db.session.add(transaction)
        db.session.flush() # Get ID for transaction

        # Create Lines and Adjust Inventory
        for line in line_items_data:
            item = line['item']
            qty = line['qty']
            
            # Create transaction line
            tx_line = TransactionLine(
                transaction_id=transaction.id,
                item_id=item.id,
                qty=qty,
                unit_price_cents=line['price']
            )
            db.session.add(tx_line)

            # Adjust stock (Inventory Logic)
            adjust_stock(
                item_id=item.id,
                delta_qty=-qty,
                event_type="SALE",
                ref_type="transaction",
                ref_id=transaction.id,
                user_id=user_id
            )

        db.session.commit()
        return transaction

    except Exception as e:
        db.session.rollback()
        raise e
