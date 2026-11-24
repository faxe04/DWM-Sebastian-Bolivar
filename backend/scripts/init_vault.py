"""Vault de desarrollo: configura un token que solo lee los secretos del gateway."""
import os
import time
from pathlib import Path
import httpx

def main():
    directory = Path(os.getenv("SECRET_DIR", "/run/secrets"))
    address = os.getenv("VAULT_ADDR", "http://vault:8200")
    root_token = (directory / "vault_root_token").read_text().strip()
    gateway_token = (directory / "vault_gateway_token").read_text().strip()
    with httpx.Client(base_url=address, headers={"X-Vault-Token": root_token}, timeout=5) as client:
        for attempt in range(30):
            try:
                if client.get("/v1/sys/health").status_code == 200:
                    break
            except httpx.RequestError:
                pass
            time.sleep(1)
        values = {name: (directory / name).read_text().strip() for name in (
            "auth_introspection_secret", "inventory_gateway_secret",
            "clients_gateway_secret", "orders_gateway_secret", "payments_gateway_secret", "graphql_gateway_secret")}
        client.post("/v1/secret/data/gateway", json={"data": values}).raise_for_status()
        policy = 'path "secret/data/gateway" { capabilities = ["read"] }'
        client.put("/v1/sys/policies/acl/gateway", json={"policy": policy}).raise_for_status()
        # Reinicializar no necesita recrear un token que ya existe.
        lookup = client.post("/v1/auth/token/lookup", json={"token": gateway_token})
        if lookup.status_code != 200:
            client.post("/v1/auth/token/create", json={"id": gateway_token, "policies": ["gateway"],
                "no_default_policy": True, "ttl": "24h", "renewable": True}).raise_for_status()
    print("Vault configurado para desarrollo, sin imprimir secretos.")

if __name__ == "__main__":
    main()
