from models import db, Item, Issue, IssueLine, Teacher
from services.inventory import adjust_stock
from services.signatures import save_signature

def process_issue(user_id, teacher_id, cart_items, signature_data, instance_path):
    if not cart_items:
        raise ValueError("Cart is empty")
    
    if not signature_data:
        raise ValueError("Signature required")

    try:
        # Save Signature
        sig_path = save_signature(signature_data, instance_path, prefix=f"issue_t{teacher_id}")

        # Create Issue Record
        issue = Issue(
            teacher_id=teacher_id,
            user_id=user_id,
            signature_path=sig_path
        )
        db.session.add(issue)
        db.session.flush()

        # Update Teacher Reference Signature if missing
        teacher = Teacher.query.get(teacher_id)
        if teacher and not teacher.signature_path:
            teacher.signature_path = sig_path
            db.session.add(teacher)

        # Process Items
        for item_id, qty in cart_items.items():
            qty = int(qty)
            if qty <= 0: continue
            
            item = Item.query.get(item_id)
            if not item: continue # Skip invalid

            # Decrement Stock
            if item.stock_on_hand < qty:
                # MVP: allow negative? Requirements imply strictness, but let's allow negative for internal issuance 
                # unless strict mode requested. Let's allow it but warn. 
                # Actually user prompt "validate each item has enough stock (NO negative stock in MVP)" from PREVIOUS prompt.
                # CURRENT prompt says: "Internal school store issuance tracking". 
                # I will stick to NO negative stock to be safe and robust.
                raise ValueError(f"Insufficient stock for {item.name}")

            # Create Line
            line = IssueLine(issue_id=issue.id, item_id=item.id, qty=qty)
            db.session.add(line)

            # Inventory Log
            adjust_stock(
                item_id=item.id,
                delta_qty=-qty,
                event_type="ISSUE",
                ref_type="issue",
                ref_id=issue.id,
                user_id=user_id
            )

        db.session.commit()
        return issue

    except Exception as e:
        db.session.rollback()
        raise e
