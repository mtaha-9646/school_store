import unittest
from flask import session
from app import app, db, User, Item, Teacher, Department, InventoryLog

class TestFlow(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Seed Data
        self.user = User(name="Admin", role="admin")
        self.dept = Department(name="Science")
        db.session.add_all([self.user, self.dept])
        db.session.commit()
        
        self.teacher = Teacher(name="Mr. Test", department_id=self.dept.id)
        self.item = Item(name="Pen", sku="PEN-01", stock_on_hand=100, barcode="12345")
        db.session.add_all([self.teacher, self.item])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_cart_add_htmx(self):
        with self.app as c:
            with c.session_transaction() as sess:
                sess['user_id'] = self.user.id
                
            # Simulate HTMX POST to add to cart
            resp = c.post('/hx/cart/add', data={'item_id': self.item.id, 'qty': 5})
            self.assertEqual(resp.status_code, 200)
            
            # Check session
            with c.session_transaction() as sess:
                cart = sess.get('cart', {})
                self.assertIn(str(self.item.id), cart)
                self.assertEqual(cart[str(self.item.id)], 5)

    def test_checkout_process(self):
        with self.app as c:
            # 1. Add to cart
            with c.session_transaction() as sess:
                sess['user_id'] = self.user.id
                sess['cart'] = {str(self.item.id): 10}
            
            # 2. Submit checkout form
            # Use valid header for base64
            sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            resp = c.post('/checkout/complete', data={
                'teacher_id': self.teacher.id,
                'signature_data': sig
            }, follow_redirects=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b'Items issued successfully', resp.data)
            
            # 3. Verify Stock Deduction
            item = Item.query.get(self.item.id)
            self.assertEqual(item.stock_on_hand, 90) # 100 - 10
            
            # 4. Verify Log
            log = InventoryLog.query.filter_by(event_type="ISSUE").first()
            self.assertIsNotNone(log)
            self.assertEqual(log.delta_qty, -10)
