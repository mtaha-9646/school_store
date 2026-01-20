from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, UniqueConstraint
from sqlalchemy.engine import Engine
from datetime import datetime

db = SQLAlchemy()

# SQLite Optimization
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" or "staff"

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    email = db.Column(db.String(120), nullable=True)
    signature_path = db.Column(db.String(255), nullable=True) # Reference signature

    department = db.relationship('Department', backref='teachers')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(50), unique=True, nullable=True, index=True)
    stock_on_hand = db.Column(db.Integer, default=0, nullable=False)
    reorder_level = db.Column(db.Integer, default=5, nullable=False)
    active = db.Column(db.Boolean, default=True)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signature_path = db.Column(db.String(255), nullable=False) # Strict audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    teacher = db.relationship('Teacher', backref='issues')
    user = db.relationship('User', backref='issues')
    lines = db.relationship('IssueLine', backref='issue', lazy=True)

class IssueLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

    item = db.relationship('Item')

class InventoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # RESTOCK, ISSUE, ADJUST, VOID
    delta_qty = db.Column(db.Integer, nullable=False)
    ref_type = db.Column(db.String(50))
    ref_id = db.Column(db.Integer, nullable=True)
    note = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item = db.relationship('Item')
    
    __table_args__ = (
        db.Index('idx_inv_item_created', 'item_id', 'created_at'),
    )
