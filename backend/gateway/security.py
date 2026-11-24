import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import config


security = HTTPBearer(auto_error=False)


async def get_gateway_secrets():
    if not config.VAULT_TOKEN:
        raise HTTPException(503, "Vault no configurado")

    url = f"{config.VAULT_ADDR.rstrip('/')}/v1/secret/data/gateway"
    headers = {"X-Vault-Token": config.VAULT_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)

    except httpx.RequestError:
        raise HTTPException(
            status_code=503, 
            detail="Vault no disponible"
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=503, 
            detail="No se pudieron obtener los secretos"
        )

    try:
        values = response.json()["data"]["data"]

        if not isinstance(values, dict):
            raise ValueError()

        return values
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=503, 
            detail="Secretos de Vault inválidos"
        )
    

async def authenticate_client(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if credentials is None or not credentials.credentials or len(credentials.credentials) > 512:
        raise HTTPException(
            status_code=401,
            detail="Bearer token requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    values = await get_gateway_secrets()
    auth_secret = values.get("auth_introspection_secret")

    if not isinstance(auth_secret, str) or not auth_secret:
        raise HTTPException(
            status_code=503, 
            detail="Falta secreto de Auth"
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{config.AUTH_SERVICE_URL.rstrip('/')}/introspect",
                json={"token": credentials.credentials},
                headers={
                    "X-Gateway-Auth-Secret": auth_secret,
                    "X-Request-ID": request.state.request_id,
                },
            )
    except httpx.RequestError:
        raise HTTPException(503, "Authentication Service no disponible") from None

    if response.status_code != 200:
        raise HTTPException(503, "No se pudo verificar la sesion")

    try:
        identity = response.json()
        if not isinstance(identity, dict) or not isinstance(identity["active"], bool):
            raise ValueError()
        if identity["active"] is False:
            raise HTTPException(401, "Token invalido o expirado")

        user_id = identity["user_id"]
        username = identity["username"]
        roles = identity["roles"]

        if not isinstance(user_id, str) or not user_id.isascii() or not user_id.isdigit():
            raise ValueError()
        
        if int(user_id) <= 0:
            raise ValueError()
        
        if not isinstance(username, str) or not username.strip() or len(username) > 254:
            raise ValueError()
        
        if any(ord(char) < 32 or ord(char) == 127 for char in username):
            raise ValueError()
        
        if not isinstance(roles, list) or not roles:
            raise ValueError()
        
        if not all(isinstance(role, str) and role in ("client", "admin") for role in roles):
            raise ValueError()
        
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=502, 
            detail="Respuesta de identidad invalida"
        )

    return {
        "user_id": user_id, 
        "username": username, 
        "roles": roles
    }


async def require_admin(identity=Depends(authenticate_client)):
    if "admin" not in identity["roles"]:
        raise HTTPException(403, "Permisos insuficientes")
    return identity
