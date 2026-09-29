import os
import secrets
from fastapi import FastAPI, Header, HTTPException, Depends


app = FastAPI(
    title="Servicio 2",
    description="API ubicada en local host enrutada por API gateway"
)

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET")

if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError("INTERNAL_GATEWAY_SECRET no está configurado")


def verify_gateway(x_gateway_secret: str = Header(default="")):
    valid = secrets.compare_digest(
        x_gateway_secret, 
        INTERNAL_GATEWAY_SECRET
    )

    if not valid:
        raise HTTPException(
            status_code=403, 
            detail="Solicitud no autorizada desde Gateway"
        )

@app.get("/health", dependencies=[Depends(verify_gateway)])
def health():
    return {
        "status": "Ok",
        "service": "Backend API 2"
    }


@app.get("/productos", dependencies=[Depends(verify_gateway)])
def products(x_authenticated_client=Header(default=None)):
    return {
        "authenticated_client": x_authenticated_client,
        "productos": [
            {"id": 1, "nombre": "Café Colombia", "precio": 7990},
            {"id": 2, "nombre": "Croissant Clásico", "precio": 3500}
        ]
    }


@app.get("/ordenes", dependencies=[Depends(verify_gateway)])
def orders(x_authenticated_client=Header(default=None)):
    return {
        "authenticated_client": x_authenticated_client,
        "ordenes": [
            {"id": 10, "status": "paid"},
            {"id": 11, "status": "pending"}
        ]
    }
