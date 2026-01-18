import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'dev-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'store.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Instance path for file saves
    INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
