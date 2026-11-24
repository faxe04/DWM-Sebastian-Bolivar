import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from mysql.connector import Error as DatabaseError, IntegrityError
from . import db
from . import config
from .schemas import ClientInput, Verification, ReceiptMail
from .security import current_user, require_admin, check_secret, read_secret

from backend.request_logging import install, REQUEST_ID


app = FastAPI(title="Clientes - Aroma & Café", docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    if isinstance(exc, IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Correo ya registrado"})
    return JSONResponse(status_code=503, content={"detail": "Persistencia no disponible"})


def existing(user_id):
    row = db.get_client(user_id)
    if row is None:
        raise HTTPException(404, "Cliente no encontrado")
    return row


@app.get("/health")
def health(user=Depends(current_user)):
    return {"status": "ok", "service": "clients"}


@app.get("/clients/me")
def my_profile(user=Depends(current_user)):
    return existing(user["id"])


@app.post("/clients/me", status_code=201)
def create_profile(profile: ClientInput, user=Depends(current_user)):
    return db.save_client(user["id"], profile.model_dump(), create=True)


@app.put("/clients/me")
def update_profile(profile: ClientInput, user=Depends(current_user)):
    return db.save_client(user["id"], profile.model_dump())


@app.post("/clients/me/verification", status_code=202)
def send_verification(user=Depends(current_user)):
    if not config.DEMO_MODE:
        raise HTTPException(503, "Proveedor de correo real pendiente de configurar")
    
    db.send_verification(user["id"])
    return {"adapter": "dummy", "real_email_sent": False, "message": "Revisa la bandeja de demostración"}


@app.post("/clients/verify-email")
def verify_email(body: Verification, x_gateway_secret: str = Header(default="")):
    check_secret(x_gateway_secret, "INTERNAL_GATEWAY_SECRET")
    db.verify_email(body.token)
    return {"email_verified": True, "adapter": "dummy"}


@app.get("/admin/clients")
def list_clients(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(require_admin)):
    return db.list_clients(skip, limit)


@app.get("/admin/clients/{user_id}")
def get_client(user_id: int = Path(gt=0), user=Depends(require_admin)):
    return existing(user_id)


@app.put("/admin/clients/{user_id}")
def update_client(profile: ClientInput, user_id: int = Path(gt=0), user=Depends(require_admin)):
    return db.save_client(user_id, profile.model_dump())


@app.delete("/admin/clients/{user_id}", status_code=204)
def delete_client(user_id: int = Path(gt=0), user=Depends(require_admin)):
    if not db.deactivate(user_id):
        raise HTTPException(404, "Cliente no encontrado")
    return Response(status_code=204)


@app.get("/admin/mailbox")
def mailbox(user=Depends(require_admin)):
    if not config.DEMO_MODE:
        raise HTTPException(404, "Bandeja disponible solo en demostración")
    return db.mailbox()


@app.get("/internal/clients/{user_id}")
def internal_client(user_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "ORDERS_CLIENTS_SECRET")
    row = existing(user_id)

    return {
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "address": row["address"],
        "email_verified": row["email_verified"]
    }


# ===== Administration =====
@app.post("/admin/clients/{user_id}", status_code=201)
def create_client(body: ClientInput, user_id: int = Path(gt=0), user=Depends(require_admin)):
    try:
        response = httpx.get(config.AUTH_SERVICE_URL + f"/internal/users/{user_id}",
            headers={"X-Service-Secret": read_secret("CLIENTS_AUTH_SECRET"), "X-Request-ID": REQUEST_ID.get()}, timeout=5)
        
    except httpx.RequestError:
        raise HTTPException(503, "Auth no disponible") from None
    
    if response.status_code != 200:
        raise HTTPException(409 if response.status_code in (404,409) else 503, "Se requiere una cuenta activa")
    
    return db.save_client(user_id, body.model_dump(), create=True)


@app.post("/admin/clients/{user_id}/verification", status_code=202)
def admin_send_verification(user_id: int = Path(gt=0), user=Depends(require_admin)):
    if not config.DEMO_MODE:
        raise HTTPException(
            status_code=503, 
            detail="Proveedor de correo pendiente"
        )
    
    db.send_verification(user_id)
    return {"adapter": "dummy", "real_email_sent": False}


@app.post("/internal/clients/{user_id}/receipts")
def queue_receipt(body: ReceiptMail, user_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "ORDERS_CLIENTS_SECRET")
    if not config.DEMO_MODE:
        raise HTTPException(
            status_code=503,
            detail="Proveedor de correo pendiente"
        )
    
    mail_id = db.queue_receipt(user_id, body.sale_id, body.message)

    return {
        "queued": True,
        "adapter": "dummy",
        "real_email_sent": False,
        "mail_id": mail_id
    }


install(app)
