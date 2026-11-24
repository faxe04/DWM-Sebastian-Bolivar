import secrets
from . import config
from fastapi import Depends, Header, HTTPException


def verify_gateway(x_gateway_secret: str = Header(default="")):
    expected = config.INTERNAL_GATEWAY_SECRET
    if not expected:
        raise HTTPException(
            status_code=503, 
            detail="Seguridad del servicio no configurada"
            )
    
    if not secrets.compare_digest(x_gateway_secret.encode(), expected.encode()):
        raise HTTPException(
            status_code=403, detail="Componente no autorizado"
        )


def require_admin(
    x_authenticated_user: str = Header(default=""),
    x_authenticated_roles: str = Header(default=""),
    gateway=Depends(verify_gateway),
):
    roles = set(x_authenticated_roles.split(","))
    if not x_authenticated_user or not roles.intersection({"admin"}) or "admin" not in roles:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para administrar productos"
        )


def check_secret(received):
    value = config.ORDERS_INVENTORY_SECRET
    if not value:
        raise HTTPException(
            status_code=503, 
            detail="Falta configuración de integración"
        )

    if not secrets.compare_digest(received.encode(), value.encode()):
        raise HTTPException(
            status_code=403, 
            detail="Componente no autorizado"
        )
