
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ===== Vault =====
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")

token_file = os.getenv("VAULT_TOKEN_FILE")

VAULT_TOKEN = (
    Path(token_file).read_text(encoding="utf-8").strip()
    if token_file
    else os.getenv("VAULT_TOKEN", "")
)

# ===== Servicios =====
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8100")

INVENTORY_URL = os.getenv("INVENTORY_URL", "http://localhost:9000")

ORDERS_URL = os.getenv("ORDERS_URL", "http://localhost:9100")

CLIENTS_URL = os.getenv("CLIENTS_URL", "http://localhost:9200")

PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://localhost:9300")

GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://localhost:9400")

# ===== Enrutamiento =====
ROUTES = {
    "inventory": INVENTORY_URL,
    "products": INVENTORY_URL,
    "orders": ORDERS_URL,
    "clients": CLIENTS_URL,
    "payments": PAYMENTS_URL,
    "graphql": GRAPHQL_URL,
}
