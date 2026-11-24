import json
from datetime import date
from html import escape
import httpx
from fastapi import FastAPI, Depends, Header, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse
from mysql.connector import Error as DatabaseError
from . import db, config
from .schemas import OrderInput, StatusInput, Cancellation, PaidInput, SaleInput
from .security import current_user, require_admin, read_secret, check_secret
from backend.request_logging import install, REQUEST_ID


app = FastAPI(
    title="Pedidos - Aroma & Café", 
    docs_url=None, 
    redoc_url=None, 
    openapi_url=None
)


@app.exception_handler(DatabaseError)
async def database_error(request: Request, exc: DatabaseError):
    return JSONResponse(status_code=503, content={"detail": "Persistencia no disponible"})


def call_service(service, method, path, secret_name, body=None):
    urls = {
        "CLIENTS": config.CLIENTS_URL,
        "INVENTORY": config.INVENTORY_URL,
        "PAYMENTS": config.PAYMENTS_URL,
    }
    target = urls.get(service)
    if not target:
        raise HTTPException(
            status_code=503, 
            detail="Servicio no configurado"
        )
    
    headers = {
        "X-Service-Secret": read_secret(secret_name),
        "X-Request-ID": REQUEST_ID.get(),
    }
    try:
        response = httpx.request(
            method, target.rstrip("/") + path,
            json=body, headers=headers, timeout=8,
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=503, 
            detail="Servicio de " + service.lower() + " no disponible; puedes reintentar"
        )
    
    if response.status_code >= 400:
        raise HTTPException(
            status_code=409 if response.status_code in (400, 404, 409, 422) else 503, 
            detail="Integracion rechazada por " + service.lower()
        )
    
    return response.json() if response.content else None



def reserve(order_id, items):
    return call_service("INVENTORY", "POST", f"/internal/reservations/{order_id}", "ORDERS_INVENTORY_SECRET", {"items": items})


def release(order_id):
    call_service("PAYMENTS", "POST", f"/internal/orders/{order_id}/cancel", "ORDERS_PAYMENTS_SECRET")
    call_service("INVENTORY", "DELETE", f"/internal/reservations/{order_id}", "ORDERS_INVENTORY_SECRET")


def refund_and_release(order_id):
    call_service("PAYMENTS", "POST", f"/internal/orders/{order_id}/refund", "ORDERS_PAYMENTS_SECRET")
    call_service("INVENTORY", "DELETE", f"/internal/reservations/{order_id}", "ORDERS_INVENTORY_SECRET")


def owned(order_id, user):
    row = db.get_order(order_id)
    if not row or (not user["admin"] and row["user_id"] != user["id"]):
        raise HTTPException(
            status_code=404, 
            detail="Pedido no encontrado"
        )
    return row


def validate_delivery(client):
    address = client.get("address")
    if not isinstance(address, str) or not address.strip():
        raise HTTPException(
            status_code=409, 
            detail="El cliente debe registrar una dirección"
        )


# ===== System =====
@app.get("/health")
def health(user=Depends(current_user)):
    return {"status": "ok", "service": "orders"}


@app.post("/orders", status_code=201)
def create_order(body: OrderInput, user=Depends(current_user), idempotency_key: str = Header(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")):
    client = call_service("CLIENTS", "GET", f"/internal/clients/{user['id']}", "ORDERS_CLIENTS_SECRET")
    # if not client["email_verified"]:
    #     raise HTTPException(
    #         status_code=409, 
    #         detail="Debes verificar el correo"
    #     )
    
    if body.delivery_method == "delivery":
        validate_delivery(client)

    row = db.begin_order(user["id"], idempotency_key, body.model_dump(), client)
    return db.finish_order(row["id"], reserve)


@app.get("/orders")
def list_orders(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(current_user)):
    return db.list_orders(user["id"], skip, limit)


@app.get("/orders/{order_id}")
def get_order(order_id: int = Path(gt=0), user=Depends(current_user)):
    return owned(order_id, user)


@app.post("/orders/{order_id}/cancel")
def cancel_order(body: Cancellation, order_id: int = Path(gt=0), user=Depends(current_user)):
    action = db.cancel(order_id, user, body.reason)

    if action == "release":
        release(order_id)

    elif action == "refund":
        refund_and_release(order_id)

    if action in ("release", "refund"):
        db.finish_cancellation(order_id)

    return owned(order_id, user)


@app.get("/admin/orders")
def admin_orders(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(require_admin)):
    return db.list_orders(None, skip, limit)


@app.put("/admin/orders/{order_id}/status")
def advance_order(body: StatusInput, order_id: int = Path(gt=0), user=Depends(require_admin)):
    db.advance(order_id, body.status)
    return owned(order_id, user)


@app.get("/internal/orders/{order_id}")
def payment_context(order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "PAYMENTS_ORDERS_SECRET")
    row = db.get_order(order_id)
    if not row:
        raise HTTPException(
            status_code=404, 
            detail="Pedido no encontrado"
        )
    
    return {key: row[key] for key in ("id", "user_id", "total", "currency", "status")}


@app.post("/internal/orders/{order_id}/paid")
def mark_paid(body: PaidInput, order_id: int = Path(gt=0), x_service_secret: str = Header(default="")):
    check_secret(x_service_secret, "PAYMENTS_ORDERS_SECRET")
    db.mark_paid(order_id, body.payment_id, body.amount)
    return {"status": "ok"}


# ===== Ventas, boletas y despacho =====
def send_receipt(sale, user_id):
    if sale["receipt_sent"]:
        return
    message = "DEMO. Boleta " + str(sale["id"]) + ": " + json.dumps(sale["receipt"], ensure_ascii=False)
    try:
        response = httpx.post(config.CLIENTS_URL.rstrip("/") + f"/internal/clients/{user_id}/receipts",
            headers={"X-Service-Secret": read_secret("ORDERS_CLIENTS_SECRET"), "X-Request-ID": REQUEST_ID.get()},
            json={"sale_id": sale["id"], "message": message}, timeout=5)
        
    except httpx.RequestError:
        raise HTTPException(503, "Venta guardada; repite POST /admin/sales para reenviar la boleta")
    
    if response.status_code != 200:
        raise HTTPException(503, "Venta guardada; revisa el correo del cliente y reintenta el envío")
    
    db.mark_receipt_sent(sale["id"])


@app.post("/admin/sales", status_code=201)
def sell(body: SaleInput, user=Depends(require_admin)):
    sale, client_id = db.create_sale(body, user)
    send_receipt(sale, client_id)
    return db.get_sale(body.order_id, user)


@app.get("/admin/cash-registers")
def registers(user=Depends(require_admin)):
    return db.list_registers()


@app.get("/orders/{order_id}/receipt")
def receipt(order_id: int = Path(gt=0), user=Depends(current_user)):
    return db.get_sale(order_id, user)


def printable(title, subtitle, items, total=None):
    lines = "".join("<tr><td>" + escape(str(i["name"])) + "</td><td>" + str(i["quantity"]) +
                    "</td><td>" + str(i["price"]) + "</td></tr>" for i in items)
    return "<!doctype html><html lang='es'><meta charset='utf-8'><title>" + escape(title) + "</title><body><h1>" + escape(title) + "</h1><p>" + escape(subtitle) + "</p><table><tr><th>Producto</th><th>Cantidad</th><th>Precio CLP</th></tr>" + lines + "</table>" + ("<p>Total CLP: " + str(total) + "</p>" if total is not None else "") + "</body></html>"


@app.get("/orders/{order_id}/receipt/print", response_class=HTMLResponse)
def print_receipt(order_id: int = Path(gt=0), user=Depends(current_user)):
    sale = db.get_sale(order_id, user)
    document = sale["receipt"]
    return printable("Boleta DEMO " + str(sale["id"]), "SIN VALIDEZ TRIBUTARIA. " + document["customer"] + ". Estado pedido: " + sale["order_status"], document["items"], sale["total"])


@app.get("/admin/sales/report")
def sales_report(start_date: date, end_date: date, user=Depends(require_admin)):
    return db.sales_report(start_date, end_date)


@app.get("/admin/dispatch")
def dispatch_queue(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(require_admin)):
    return db.list_dispatch(skip, limit)


@app.get("/admin/orders/{order_id}/dispatch", response_class=HTMLResponse)
def print_dispatch(order_id: int = Path(gt=0), user=Depends(require_admin)):
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(404, "Pedido no encontrado")
    
    if order["status"] not in ("PAID", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"):
        raise HTTPException(409, "Solo se imprimen órdenes pagadas")
    
    address = order["address_snapshot"] or {}
    return printable("Orden de despacho " + str(order_id),
        str(order["created_at"]) + " | " + order["status"] + " | " + address.get("full_name", "") +
        " | " + (address.get("address", "") if order["delivery_method"] == "delivery" else "Retiro en local"),
        order["items"])


install(app)
