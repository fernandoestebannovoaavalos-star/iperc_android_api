import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'iperc-cajamarca-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:admin123@localhost/iperc_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de Email
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'fernandoestebannovoaavalos@gmail.com'
    MAIL_PASSWORD = 'titdyaoqncicaxwi'
    MAIL_DEFAULT_SENDER = 'fernandoestebannovoaavalos@gmail.com'
    SERVER_NAME = None