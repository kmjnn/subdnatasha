import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'supersecretkey123!'  # Замените на надежный ключ
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:0000@localhost/education_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True