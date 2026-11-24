from contextlib import contextmanager
import mysql.connector
from fastapi import HTTPException
from . import config
import json
import hashlib
from datetime import timedelta


@contextmanager
def connection():
    if not config.DB_USER:
        raise RuntimeError("DB_USER no esta configurado")
    
    if not config.DB_PASS:
        raise RuntimeError("DB_PASS no esta configurado")
    
    if not config.DB_NAME:
        raise RuntimeError("DB_NAME no esta configurado")

    conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASS,
        database=config.DB_NAME,
        connection_timeout=5,
        autocommit=False,
    )

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def decode(row):
    if row:
        for name in ("items", "address_snapshot"):
            if isinstance(row[name], str):
                row[name] = json.loads(row[name])
    return row


def get_order(order_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
        return decode(cursor.fetchone())


def list_orders(user_id, skip, limit):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        condition = " WHERE user_id=%s" if user_id is not None else ""
        values = (user_id, limit, skip) if user_id is not None else (limit, skip)
        cursor.execute("SELECT * FROM orders" + condition + " ORDER BY id DESC LIMIT %s OFFSET %s", values)
        return [decode(row) for row in cursor.fetchall()]


def begin_order(user_id, key, body, address):
    payload = json.dumps(body, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT INTO orders(user_id,request_key,request_hash,delivery_method,address_snapshot,items) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)", (user_id, key, digest, body["delivery_method"], json.dumps(address), json.dumps(body["items"])))
        cursor.execute("SELECT * FROM orders WHERE user_id=%s AND request_key=%s FOR UPDATE", (user_id, key))
        row = cursor.fetchone()
        if row["request_hash"] != digest:
            raise HTTPException(
                status_code=409, 
                detail="Idempotency-Key ya usada para otro pedido"
            )
        return decode(row)


def finish_order(order_id, reserve):
    row = get_order(order_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado"
        )

    if row["status"] != "CREATING":
        return row

    items = reserve(order_id, row["items"])
    total = sum(item["price"]*item["quantity"] for item in items)
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        current = decode(cursor.fetchone())

        if current["status"] == "CREATING":
            cursor.execute("UPDATE orders SET items=%s, total=%s, status='PENDING_PAYMENT' WHERE id=%s", (json.dumps(items), total, order_id))
            current.update(items=items, total=total, status="PENDING_PAYMENT")

        return current


def mark_paid(order_id, payment_id, amount):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, 
                detail="Pedido no encontrado"
            )
        
        if row["total"] != amount:
            raise HTTPException(
                status_code=409, 
                detail="Monto incorrecto"
            )
        
        if row["payment_id"] == payment_id:
            return
        
        if row["status"] != "PENDING_PAYMENT":
            raise HTTPException(
                status_code=409, 
                detail="Pedido no admite este pago"
            )
        
        cursor.execute("UPDATE orders SET status='PAID',payment_id=%s WHERE id=%s", (payment_id, order_id))


def advance(order_id, status):
    transitions = {"PAID": "PREPARING", "PREPARING": "READY", "READY": "OUT_FOR_DELIVERY", "OUT_FOR_DELIVERY": "DELIVERED"}
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, 
                detail="Pedido no encontrado"
            )
        
        next_status = "DELIVERED" if row["status"] == "READY" and row["delivery_method"] == "pickup" else transitions.get(row["status"])
        if status != next_status:
            raise HTTPException(
                status_code=409, 
                detail="Transición inválida; debe pagarse antes de preparar"
            )
        
        cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))


def cancel(order_id, user, reason):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,))
        row = cursor.fetchone()

        if not row or (not user["admin"] and row["user_id"] != user["id"]):
            raise HTTPException(
                status_code=404, 
                detail="Pedido no encontrado"
            )
        
        if row["status"] == "CANCELLED":
            return "done"
        
        if row["status"] == "CANCELLING":
            if row["payment_id"] is not None:
                return "refund" if user["admin"] else "requested"
            return "release"
        
        if row["status"] in ("CREATING", "PENDING_PAYMENT"):
            cursor.execute("UPDATE orders SET status='CANCELLING', cancellation_requested=TRUE, cancellation_reason=%s WHERE id=%s", (reason, order_id))
            return "release"

        if row["status"] == "PAID" and user["admin"]:
            cursor.execute("UPDATE orders SET status='CANCELLING', cancellation_requested=TRUE, cancellation_reason=%s WHERE id=%s", (reason, order_id))
            return "refund"
        
        cursor.execute("UPDATE orders SET cancellation_requested=TRUE, cancellation_reason=%s WHERE id=%s", (reason, order_id))

        return "requested"


def finish_cancellation(order_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("UPDATE orders SET status='CANCELLED' WHERE id=%s AND status='CANCELLING'", (order_id,))


def ping():
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def decode_sale(row):
    if row and isinstance(row["receipt"], str):
        row["receipt"] = json.loads(row["receipt"])
    return row


def get_sale(order_id, user):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT s.*,o.user_id,o.status AS order_status FROM sales s JOIN orders o ON o.id=s.order_id WHERE s.order_id=%s", (order_id,))
        row = decode_sale(cursor.fetchone())
        if not row or (not user["admin"] and row["user_id"] != user["id"]):
            raise HTTPException(
                status_code=404, 
                detail="Boleta no encontrada"
            )
        
        return row


def create_sale(body, cashier):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (body.order_id,))
        order = decode(cursor.fetchone())
        if not order or order["status"] not in ("PAID", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"):
            raise HTTPException(
                status_code=409, 
                detail="Venta requiere un pedido pagado de un cliente registrado"
            )
        
        cursor.execute("SELECT * FROM sales WHERE order_id=%s", (body.order_id,))
        previous = cursor.fetchone()
        if previous:
            if previous["register_id"] != body.register_id:
                raise HTTPException(
                    status_code=409, 
                    detail="La venta ya pertenece a otra caja"
                )
            
            return decode_sale(previous), order["user_id"]
        
        cursor.execute("SELECT id FROM cash_registers WHERE id=%s AND active=TRUE", (body.register_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404, 
                detail="Caja no disponible"
            )
        
        receipt = {
            "document": "BOLETA DEMO - SIN VALIDEZ TRIBUTARIA", 
            "order_id": order["id"],
            "customer": (order["address_snapshot"] or {}).get("full_name", "Cliente registrado"),
            "items": order["items"], 
            "total": order["total"], 
            "currency": "CLP"
        }
        cursor.execute("INSERT INTO sales(order_id,cashier_user_id,register_id,total,receipt) VALUES (%s,%s,%s,%s,%s)", (order["id"], cashier["id"], body.register_id, order["total"], json.dumps(receipt, ensure_ascii=False)))
        cursor.execute("SELECT * FROM sales WHERE id=%s", (cursor.lastrowid,))

        return decode_sale(cursor.fetchone()), order["user_id"]


def list_registers():
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM cash_registers ORDER BY id")
        return cursor.fetchall()



def sales_report(start_date, end_date):
    if end_date < start_date or (end_date - start_date).days > 366:
        raise HTTPException(
            status_code=422, 
            detail="Período inválido; máximo 366 días"
        )
    
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS sales_count, 
            COALESCE(SUM(s.total),0) AS gross_total,
            COALESCE(SUM(CASE WHEN o.status IN ('CANCELLED','CANCELLING') THEN s.total ELSE 0 END),0) AS cancelled_total,
            COALESCE(SUM(CASE WHEN o.status NOT IN ('CANCELLED','CANCELLING') THEN s.total ELSE 0 END),0) AS net_total
            FROM sales s JOIN orders o ON o.id=s.order_id WHERE s.created_at >= %s AND s.created_at < %s
            """, (start_date, end_date + timedelta(days=1))
        )
        totals = cursor.fetchone()
    return {
        "start_date": start_date, 
        "end_date": end_date, 
        "timezone": "UTC", 
        "currency": "CLP", 
        **totals
    }


def list_dispatch(skip, limit):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT id,user_id,status,delivery_method,created_at FROM orders WHERE status IN ('PAID','PREPARING','READY') ORDER BY created_at,id LIMIT %s OFFSET %s", (limit, skip))
        return cursor.fetchall()


def mark_receipt_sent(sale_id):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("UPDATE sales SET receipt_sent=TRUE WHERE id=%s", (sale_id,))

