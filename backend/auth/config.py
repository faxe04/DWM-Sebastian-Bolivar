import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


def setting(name, default=""):
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()

    return os.getenv(name, default)


# ===== DB settings =====
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASS = setting("DB_PASS")
DB_NAME = os.getenv("DB_NAME", "")

# ===== Secutiry settings =====
AUTH_INTROSPECTION_SECRET = setting("AUTH_INTROSPECTION_SECRET")
CLIENTS_AUTH_SECRET = setting("CLIENTS_AUTH_SECRET")

# ===== DB settings =====
TOKEN_LIFETIME_MINUTES = 15
ITERATIONS = 600_000
