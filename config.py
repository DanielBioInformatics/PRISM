import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "PRISM_SAAS_SECRET_KEY_2026")
    DATABASE_URL = os.getenv("DATABASE_URL", "database.db")
    PDB_CACHE_FILE = os.getenv("PDB_CACHE_FILE", "pdb_ids_cache.json")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
