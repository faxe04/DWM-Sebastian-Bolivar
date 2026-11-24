import os
import hashlib
import secrets
from fastapi import Header, HTTPException, Depends
from pathlib import Path
from . import config


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), config.ITERATIONS)
    return "pbkdf2_sha256$" + str(config.ITERATIONS) + "$" + salt + "$" + digest.hex()


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256" or int(iterations) != config.ITERATIONS:
            return False
        
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return secrets.compare_digest(digest.hex(), expected)
    
    except (ValueError, TypeError):
        return False


def token_hash(token):
    # La base guarda una huella, no el token que permite usar la sesión
    return hashlib.sha256(token.encode()).hexdigest()


def verify_gateway(x_gateway_auth_secret: str = Header(default="")):
    expected = config.AUTH_INTROSPECTION_SECRET
    if not expected:
        raise HTTPException(
            status_code=503, 
            detail="Seguridad de Auth no configurada"
        )
    
    if not secrets.compare_digest(x_gateway_auth_secret.encode(), expected.encode()):
        raise HTTPException(
            status_code=403, 
            detail="Gateway no autorizado"
        )


def require_admin(
    x_authenticated_user: str = Header(default=""),
    x_authenticated_roles: str = Header(default=""),
    gateway=Depends(verify_gateway)
):
    if (
        not x_authenticated_user.isascii()
        or not x_authenticated_user.isdigit()
        or "admin" not in x_authenticated_roles.split(",")
    ):
        raise HTTPException(
            status_code=403, 
            detail="Solo administradores"
        )

    return int(x_authenticated_user)


def verify_clients(
    x_service_secret: str = Header(default="")
):
    expected = config.CLIENTS_AUTH_SECRET

    if not expected:
        raise HTTPException(
            status_code=503, 
            detail="Clave de Clients no configurada"
        )

    if not secrets.compare_digest(x_service_secret, expected):
        raise HTTPException(
            status_code=403, 
            detail="Servicio no autorizado"
        )
