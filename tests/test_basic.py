import unittest
from app import app, db, User, Item, Teacher, Department
from config import Config

class TestBasic(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()
        
        # Seed
        self.user = User(name="Test Admin", role="admin")
        self.dept = Department(name="Test Dept")
        db.session.add(self.user)
        db.session.add(self.dept)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_dashboard_load(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_item_creation(self):
        # Test Auto SKU
        response = self.app.post('/items/new', data={
            'name': 'Test Item',
            'stock_on_hand': 10,
            'sku': '', # Should trigger auto-gen
            'barcode': ''
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        item = Item.query.first()
        self.assertIsNotNone(item)
        self.assertEqual(item.name, 'Test Item')
        self.assertTrue(item.sku.startswith('SKU-'))
        self.assertEqual(item.stock_on_hand, 10)

    def test_restock_page_load(self):
        response = self.app.get('/restock')
        self.assertEqual(response.status_code, 200)

    def test_checkout_page_load(self):
        response = self.app.get('/checkout')
        self.assertEqual(response.status_code, 200)
