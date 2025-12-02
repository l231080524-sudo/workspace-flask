import os

DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql://postgres:HOLA@localhost:5432/paginaorquidea"
)

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
SQLALCHEMY_DATABASE_URI = DATABASE_URL
SQLALCHEMY_TRACK_MODIFICATIONS = False
