from app import app, db
import os

with app.app_context():
    db_path = os.path.join(app.instance_path, 'school_store.db')
    print(f"Resetting database at: {db_path}")
    
    # Drop all tables
    db.drop_all()
    print("Tables dropped.")
    
    # Create all tables
    db.create_all()
    print("Tables created.")
