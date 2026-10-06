import os
import secrets
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


app = FastAPI(title = "Local API Gateway")

security = HTTPBearer(auto_error=False)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://127.0.0.1:8100")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")

VAULT_TOKEN = os.getenv("VAULT_TOKEN")

if not VAULT_TOKEN:
    raise RuntimeError("VAULT_TOKEN no está configurado")

BACKEND_URL1 = "http://localhost:9000"
BACKEND_URL2 = "http://localhost:9100"
ROUTES = {
    "products": BACKEND_URL1,
    "orders": BACKEND_URL1,
    "productos": BACKEND_URL2,
    "ordenes": BACKEND_URL2
}


async def get_gateway_secrets():
    url = (
        f"{VAULT_ADDR}"
        "/v1/secret/data/gateway"
    )
    headers = {
        "X-Vault-Token": VAULT_TOKEN
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            url=url, 
            headers=headers
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"No fue posible acceder a Vault: {response}"
        )
    vault_response = response.json()
    return vault_response["data"]["data"]


async def authenticate_client(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer token requerido"
        )
    gateway_secrets = await get_gateway_secrets()

    introspection_secret = gateway_secrets["auth_introspection_secret"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/introspect",
                json={"token": credentials.credentials},
                headers={"X-Gateway-Auth-Secret": introspection_secret}
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service no disponible"
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Error consultado Authentication Service"
        )
    identity = response.json()
    if not identity.get("active", False):
        raise HTTPException(
            status_code=401,
            detail="Token invalido o expirado"
        )
    return {
        "user_id": identity["user_id"],
        "username": identity["username"],
        "roles": identity["roles"],
        "backend_secret": gateway_secrets["backend_shared_secret"]
    }


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request, auth=Depends(authenticate_client)):
    route = path.split("/")[0]
    backend_url = ROUTES.get(route)
    target_url = (
        f"{backend_url}/{path}"
    )
    body = await request.body()
    gateway_headers = {
        "X-Gateway-Secret": auth["backend_secret"],
        "X-Authenticated-Client": auth["user_id"],
        "X-Authenticated-User": auth["username"],
        "X-Authenticated-Roles": ",".join(auth["roles"])
    }
    content_type = request.headers.get("content-type")
    if content_type:
        gateway_headers["Content-Type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                params=request.query_params,
                content=body,
                headers=gateway_headers
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Backend no disponible")

    response_headers = {}
    if "content-type" in upstream.headers:
        response_headers["content-type"] = upstream.headers["content-type"]

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers
    )
