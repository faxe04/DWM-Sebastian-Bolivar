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
CLIENTS_URL = os.getenv("CLIENTS_URL", "http://localhost:9200")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:9000")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:9300")

# ===== Seguridad =====
INTERNAL_GATEWAY_SECRET = setting("INTERNAL_GATEWAY_SECRET")
ORDERS_CLIENTS_SECRET = setting("ORDERS_CLIENTS_SECRET")
ORDERS_INVENTORY_SECRET = setting("ORDERS_INVENTORY_SECRET")
ORDERS_PAYMENTS_SECRET = setting("ORDERS_PAYMENTS_SECRET")
PAYMENTS_ORDERS_SECRET = setting("PAYMENTS_ORDERS_SECRET")
