import os
import logging
from dotenv import load_dotenv

# .env betöltése (lokális fejlesztéshez)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "PRISM_SAAS_SECRET_KEY_2026")
    DATABASE_URL = os.getenv("DATABASE_URL", "database.db")
    PDB_CACHE_FILE = os.getenv("PDB_CACHE_FILE", "pdb_ids_cache.json")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # REDIS_URL kényszerített betöltése alapértelmezett érték nélkül
    REDIS_URL = os.getenv("REDIS_URL")

# Ellenőrzés: ha nincs REDIS_URL, dobjon hibát, ne próbálkozzon a localhost-tal
if not Config.REDIS_URL:
    logging.error("HIBA: A REDIS_URL környezeti változó nincs beállítva!")
    raise ValueError("A REDIS_URL környezeti változó hiányzik a konfigurációból.")