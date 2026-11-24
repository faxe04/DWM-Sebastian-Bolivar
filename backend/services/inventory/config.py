import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


def setting(name, default=""):
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()

    return os.getenv(name, default)


# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASS = setting("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "")

# Seguridad
INTERNAL_GATEWAY_SECRET = setting("INTERNAL_GATEWAY_SECRET", "")
ORDERS_INVENTORY_SECRET = setting("ORDERS_INVENTORY_SECRET", "")
