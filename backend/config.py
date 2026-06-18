import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Tentukan root direktori project (tempat .env berada)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # ---------- General ----------
    ENVIRONMENT: str = "development"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # ---------- Database ----------
    # Gunakan DATABASE_URL sebagai input utama dari cloud platform (seperti Neon/Render)
    DATABASE_URL: Optional[str] = None

    # Ini tetap dipertahankan jika di lokal ingin memakai konfigurasi terpisah
    DB_HOST: Optional[str] = "localhost"
    DB_PORT: Optional[int] = 5432
    DB_NAME: Optional[str] = "ecologistic_fresh_db"
    DB_USER: Optional[str] = "madhan_dev"
    DB_PASSWORD: Optional[str] = "madhan123"

    # ---------- Model ML ----------
    MODEL_PATH: str = "backend/models/random_forest_model.pkl"

    # ---------- External API Keys ----------
    GEMINI_API_KEY: str = ""
    HF_API_KEY: str = ""

    # ---------- Helper untuk path absolut ----------
    BASE_DIR: str = str(BASE_DIR)

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """
        Properti untuk menghasilkan URL database asinkron yang valid untuk SQLAlchemy + asyncpg
        """
        # 1. Jika DATABASE_URL tersedia (dari Neon / Render env)
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # Menangani penyesuaian driver asyncpg untuk database cloud
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"): # Render/Heroku kadang menggunakan format lama ini
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        
        # 2. Fallback jika DATABASE_URL tidak diset, buat manual dari konfigurasi satuan
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = (
            os.path.join(BASE_DIR, ".env") 
            if os.path.exists(os.path.join(BASE_DIR, ".env")) 
            else os.path.join(BASE_DIR, "backend", ".env")
        )
        extra = "ignore"

# Instance global yang akan di-import di seluruh aplikasi
settings = Settings()