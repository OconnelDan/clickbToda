import os

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True
    }
