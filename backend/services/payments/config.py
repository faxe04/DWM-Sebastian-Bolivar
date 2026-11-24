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
ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:9100")

# ===== Seguridad =====
INTERNAL_GATEWAY_SECRET = setting("INTERNAL_GATEWAY_SECRET")
PAYMENTS_ORDERS_SECRET = setting("PAYMENTS_ORDERS_SECRET")
ORDERS_PAYMENTS_SECRET = setting("ORDERS_PAYMENTS_SECRET")
PAYMENT_WEBHOOK_SECRET = setting("PAYMENT_WEBHOOK_SECRET")

# ===== Demostracion =====
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
