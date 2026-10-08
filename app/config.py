import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ali_kuryer.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

settings = Settings()
