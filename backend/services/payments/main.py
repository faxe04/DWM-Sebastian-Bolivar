import hashlib
import hmac
import json
import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from mysql.connector import Error as DatabaseError, IntegrityError
from pydantic import ValidationError
from . import db, config
from .schemas import PaymentInput, PaymentEvent, Simulation, TestCardInput
from .security import current_user, require_admin, read_secret, check_secret
from backend.request_logging import install, REQUEST_ID


app = FastAPI(
    title="Pagos DEMO - Aroma & Café", 
    docs_url=None, 
    redoc_url=None, 
    openapi_url=None
)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=409 if isinstance(exc, IntegrityError) else 503, 
        content={"detail": "Conflicto de pago; reintenta" if isinstance(exc, IntegrityError) else "Persistencia no disponible"}
    )


def orders_request(method, path, body=None):
    try:
        response = httpx.request(method, config.ORDERS_URL.rstrip("/") + path,
            headers={"X-Service-Secret": read_secret("PAYMENTS_ORDERS_SECRET"), "X-Request-ID": REQUEST_ID.get()}, json=body, timeout=8)
        
    except httpx.RequestError:
        raise HTTPException(503, "Pedidos no disponible; reintenta la misma operación")
    
    if response.status_code >= 400:
        raise HTTPException(409 if response.status_code in (404, 409) else 503, "Pedidos rechazó la operación")
    
    return response.json()


def demo_only():
    if not config.DEMO_MODE:
        raise HTTPException(
            status_code=503, 
            detail="Proveedor de pago real no configurado"
        )


def start_dummy(payment):
    return {**payment, "provider": "dummy", "real_charge": False, "message": "Un administrador puede simular APPROVED o REJECTED"}


def owned(payment_id, user):
    row = db.get_payment(payment_id)
    if not row or (not user["admin"] and row["user_id"] != user["id"]):
        raise HTTPException(
            status_code=404, 
            detail="Pago no encontrado"
        )
    
    return row


def process_event(raw, signature):
    expected = hmac.new(read_secret("PAYMENT_WEBHOOK_SECRET").encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(403, "Firma de pago inválida")
    
    try:
        event = PaymentEvent.model_validate_json(raw)

    except ValidationError:
        raise HTTPException(422, "Evento de pago inválido")
    
    payment = db.apply_event(event, hashlib.sha256(raw).hexdigest())
    if payment["status"] == "APPROVED" and not payment["synchronized"]:
        orders_request("POST", f"/internal/orders/{payment['order_id']}/paid", {"payment_id": payment["id"], "amount": payment["amount"]})
        db.mark_synchronized(payment["id"])

    return {"received": True, "provider": "dummy", "real_charge": False}


@app.post("/payments", status_code=201)
def create_payment(body: PaymentInput, user=Depends(current_user), idempotency_key: str = Header(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")):
    demo_only()
    order = orders_request("GET", f"/internal/orders/{body.order_id}")
    if order["user_id"] != user["id"] and not user["admin"]:
        raise HTTPException(404, "Pedido no encontrado")
    
    return start_dummy(db.create_payment(order, order["user_id"], idempotency_key))


@app.get("/payments")
def list_payments(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(current_user)):
    return db.list_payments(user["id"], skip, limit)


@app.get("/payments/{payment_id}")
def get_payment(payment_id: int = Path(gt=0), user=Depends(current_user)):
    return start_dummy(owned(payment_id, user))


@app.get("/admin/payments")
def admin_payments(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(require_admin)):
    return db.list_payments(None, skip, limit)


@app.post("/admin/payments/{payment_id}/simulate")
def simulate(body: Simulation, payment_id: int = Path(gt=0), user=Depends(require_admin)):
    demo_only()
    payment = owned(payment_id, user)
    
    raw = json.dumps({"event_id": f"dummy-{payment_id}-{body.result}", "payment_id": payment_id, "amount": payment["amount"], "currency": payment["currency"], "status": body.result}, sort_keys=True).encode()
    signature = hmac.new(read_secret("PAYMENT_WEBHOOK_SECRET").encode(), raw, hashlib.sha256).hexdigest()
    
    return process_event(raw, signature)


@app.post("/payments/webhook")
async def webhook(request: Request, x_payment_signature: str = Header(default=""), x_gateway_secret: str = Header(default="")):
    demo_only()
    check_secret(x_gateway_secret, "INTERNAL_GATEWAY_SECRET")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16384:
            raise HTTPException(413, "Evento demasiado grande")
        
    return await run_in_threadpool(process_event, bytes(raw), x_payment_signature)


@app.post("/payments/{payment_id}/test")
def test_card_payment(body: TestCardInput, payment_id: int = Path(gt=0), user=Depends(current_user)):
    demo_only()
    payment = owned(payment_id, user)
    if payment["status"] != "PENDING":
        raise HTTPException(
            status_code=409, 
            detail="Este pago ya fue procesado"
        )

    number = body.number.replace(" ", "")

    cards = {
        "0000000000000001": "APPROVED",
        "0000000000000002": "REJECTED"
    }

    result = cards.get(number)
    if result is None:
        raise HTTPException(
            status_code=422, 
            detail="Tarjeta de prueba no reconocida"
        )

    event = {
        "event_id": f"demo-card-{payment_id}-{result}",
        "payment_id": payment_id,
        "amount": payment["amount"],
        "currency": payment["currency"],
        "status": result
    }

    raw = json.dumps(event, sort_keys=True).encode()

    signature = hmac.new(
        read_secret("PAYMENT_WEBHOOK_SECRET").encode(),
        raw,
        hashlib.sha256
    ).hexdigest()

    process_event(raw, signature)
    
    return start_dummy(owned(payment_id, user))


@app.post("/internal/orders/{order_id}/cancel")
def block_order(order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "ORDERS_PAYMENTS_SECRET")
    db.block_order(order_id)
    return {"cancelled": True}


@app.post("/internal/orders/{order_id}/refund")
def refund_order(order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "ORDERS_PAYMENTS_SECRET")
    demo_only()
    db.refund_order(order_id)
    return {"status": "REFUNDED", "provider": "dummy", "real_refund": False}


@app.get("/health")
def health(user=Depends(current_user)):
    return {"status": "ok", "service": "payments"}


install(app)
