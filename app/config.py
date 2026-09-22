import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

DEV_SECRET = "dev-secret-a-changer-en-production"
DEV_JWT_SECRET = "dev-jwt-secret-a-changer-en-production"


class Config:
    """Configuration de base, partagee par tous les environnements."""

    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", DEV_JWT_SECRET)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", 15)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", 7)))

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///sante.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    SWAGGER_ENABLED = False
    LOG_LEVEL = "INFO"


class DevConfig(Config):
    DEBUG = True
    SWAGGER_ENABLED = True
    LOG_LEVEL = "DEBUG"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False
    SWAGGER_ENABLED = True
    LOG_LEVEL = "WARNING"


class ProdConfig(Config):
    DEBUG = False


config_by_name = {
    "dev": DevConfig,
    "test": TestConfig,
    "prod": ProdConfig,
}