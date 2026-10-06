import os
import secrets
from fastapi import FastAPI, Header, HTTPException, Depends


app = FastAPI(
    title="Servicio 1",
    description="API ubicada en local host enrutada por API gateway"
)

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET")

if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError("INTERNAL_GATEWAY_SECRET is not set")


def verify_gateway(x_gateway_secret: str = Header(default="")):
    valid = secrets.compare_digest(
        x_gateway_secret, 
        INTERNAL_GATEWAY_SECRET
    )

    if not valid:
        raise HTTPException(
            status_code=403, 
            detail="Unauthorized request from Gateway"
        )


@app.get("/health", dependencies=[Depends(verify_gateway)])
def health():
    return {
        "status": "Ok",
        "service": "Backend API 1"
    }


@app.get("/products", dependencies=[Depends(verify_gateway)])
def products(
    x_authenticated_client: str | None = Header(default=None),
    x_authenticated_user: str | None = Header(default=None),
    x_authenticated_roles: str | None = Header(default=None),
):
    return {
        "identity": {
            "client_id": x_authenticated_client,
            "username": x_authenticated_user,
            "roles": x_authenticated_roles
        }, 
        "products": [
            {"id": 1, "name": "Café Colombia", "price": 7990},
            {"id": 2, "name": "Croissant Clásico", "price": 3500}
        ]
    }


@app.get("/orders", dependencies=[Depends(verify_gateway)])
def orders(
    x_authenticated_client: str | None = Header(default=None),
    x_authenticated_user: str | None = Header(default=None),
    x_authenticated_roles: str | None = Header(default=None),
):
    return {
        "identity": {
            "client_id": x_authenticated_client,
            "username": x_authenticated_user,
            "roles": x_authenticated_roles
        },
        "orders": [
            {"id": 10, "status": "paid"},
            {"id": 11, "status": "pending"}
        ]
    }
