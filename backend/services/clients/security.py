import os
import secrets
from pathlib import Path
from fastapi import Depends, Header, HTTPException
from . import config


def read_secret(name):
    value = getattr(config, name, "")
    if not value:
        raise HTTPException(
            status_code=503, 
            detail="Falta configuración de integración"
        )

    return value


def check_secret(received, name):
    expected = read_secret(name)
    if not secrets.compare_digest(received.encode(), expected.encode()):
        raise HTTPException(
            status_code=403, 
            detail="Componente no autorizado"
        )


def current_user(
        x_gateway_secret: str = Header(default=""),
        x_authenticated_user: str = Header(default=""),
        x_authenticated_roles: str = Header(default="")
):
    check_secret(x_gateway_secret, "INTERNAL_GATEWAY_SECRET")
    if not x_authenticated_user.isascii() or not x_authenticated_user.isdigit():
        raise HTTPException(
            status_code=401, 
            detail="Identidad requerida"
        )
    
    roles = set(x_authenticated_roles.split(","))
    if not roles.intersection({"client", "admin"}):
        raise HTTPException(
            status_code=403, 
            detail="Rol no permitido"
        )
    
    return {"id": int(x_authenticated_user), "admin": "admin" in roles}


def require_admin(user=Depends(current_user)):
    if not user["admin"]:
        raise HTTPException(403, "Solo administradores")
    return user
