"""Preparación local: crea lo que falta, sin leer ni sobrescribir .env existentes."""
from pathlib import Path
import secrets
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

BACKEND = Path(__file__).resolve().parents[1]

def prepare_secrets():
    root = BACKEND / ".runtime"
    root.mkdir(exist_ok=True)
    for name in ("mysql_root_password", "mysql_password", "inventory_gateway_secret", "auth_db_password", "auth_introspection_secret", "demo_admin_password", "demo_client_password", "clients_db_password", "orders_db_password", "payments_db_password", "clients_gateway_secret", "orders_gateway_secret", "payments_gateway_secret", "orders_clients_secret", "orders_inventory_secret", "payments_orders_secret", "orders_payments_secret", "payment_webhook_secret", "vault_root_token", "vault_gateway_token", "graphql_gateway_secret", "clients_auth_secret"):
        target = root / name
        try:
            with target.open("x", encoding="utf-8") as output:
                output.write(secrets.token_hex(32))
            target.chmod(0o600)
            print(f"Creado: {name}")
        except FileExistsError:
            print(f"Conservado: {name}")

def prepare_env():
    for folder in ("", "auth", "gateway", "graphql", "services/inventory", "services/clients", "services/orders", "services/payments"):
        directory = BACKEND / folder
        example = directory / ".env.example"
        try:
            with (directory / ".env").open("x", encoding="utf-8") as output:
                output.write(example.read_text(encoding="utf-8"))
            print("Creado:", str(directory / ".env"))
        except FileExistsError:
            print("Conservado:", str(directory / ".env"))

def prepare_certificate():
    directory = BACKEND / ".runtime"
    directory.mkdir(exist_ok=True)
    key_file, cert_file = directory / "localhost.key", directory / "localhost.crt"
    if key_file.exists() or cert_file.exists():
        if not (key_file.exists() and cert_file.exists()):
            raise RuntimeError("Existe solo una parte del certificado; no se sobrescribe")
        print("Certificado existente conservado")
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256()))
    with key_file.open("xb") as output:
        output.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    key_file.chmod(0o600)
    with cert_file.open("xb") as output:
        output.write(certificate.public_bytes(serialization.Encoding.PEM))
    print("Certificado HTTPS local generado, válido durante 30 días")


if __name__ == "__main__":
    prepare_secrets()
    prepare_env()
    prepare_certificate()
