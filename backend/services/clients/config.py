import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def setting(name, default=""):
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()

    return os.getenv(name, default)

# ===== Database =====
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASS = setting("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "")

# ===== Servicios =====
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8100")

# ===== Seguridad =====
INTERNAL_GATEWAY_SECRET = setting("INTERNAL_GATEWAY_SECRET")
CLIENTS_AUTH_SECRET = setting("CLIENTS_AUTH_SECRET")
ORDERS_CLIENTS_SECRET = setting("ORDERS_CLIENTS_SECRET")

# ===== Demostración =====
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
