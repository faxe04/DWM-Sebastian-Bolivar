from contextlib import contextmanager
import mysql.connector
from fastapi import HTTPException
from . import config


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


def get_payment(payment_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM payments WHERE id=%s", (payment_id,))
        return cursor.fetchone()


def list_payments(user_id, skip, limit):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        condition = " WHERE user_id=%s" if user_id is not None else ""
        values = (user_id, limit, skip) if user_id is not None else (limit, skip)
        cursor.execute("SELECT * FROM payments" + condition + " ORDER BY id DESC LIMIT %s OFFSET %s", values)
        return cursor.fetchall()


def create_payment(order, user_id, key):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT IGNORE INTO payment_orders(order_id) VALUES (%s)", (order["id"],))
        cursor.execute("SELECT * FROM payment_orders WHERE order_id=%s FOR UPDATE", (order["id"],))
        reference = cursor.fetchone()
        if reference["cancelled"]:
            raise HTTPException(
                status_code=409, 
                detail="Pedido cancelado"
            )
        
        cursor.execute("SELECT * FROM payments WHERE user_id=%s AND request_key=%s", (user_id, key))
        previous = cursor.fetchone()
        if previous:
            if previous["order_id"] != order["id"]:
                raise HTTPException(
                    status_code=409, 
                    detail="Idempotency-Key ya usada para otro pedido"
                )
            return previous

        if order["status"] != "PENDING_PAYMENT":
                    raise HTTPException(
                        status_code=409, 
                        detail="Pedido no está pendiente de pago"
                    )
        
        if reference["payment_id"]:
            cursor.execute("SELECT * FROM payments WHERE id=%s", (reference["payment_id"],))
            current = cursor.fetchone()

            if current["status"] == "PENDING":
                return current

            if current["status"] != "REJECTED":
                raise HTTPException(
                    status_code=409,
                    detail="El pedido ya tiene un pago confirmado"
                )
        
        cursor.execute("INSERT INTO payments(order_id,user_id,request_key,amount,currency) VALUES (%s,%s,%s,%s,%s)", (order["id"], user_id, key, order["total"], order["currency"]))
        payment_id = cursor.lastrowid
        cursor.execute("UPDATE payment_orders SET payment_id=%s WHERE order_id=%s", (payment_id, order["id"]))
        cursor.execute("SELECT * FROM payments WHERE id=%s", (payment_id,))
        
        return cursor.fetchone()


def apply_event(event, digest):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT order_id FROM payments WHERE id=%s", (event.payment_id,))
        reference = cursor.fetchone()
        if not reference:
            raise HTTPException(
                status_code=404, 
                detail="Pago no encontrado"
            )
        
        cursor.execute("SELECT * FROM payment_orders WHERE order_id=%s FOR UPDATE", (reference["order_id"],))
        order = cursor.fetchone()

        cursor.execute("SELECT * FROM payments WHERE id=%s FOR UPDATE", (event.payment_id,))
        payment = cursor.fetchone()

        if order["cancelled"]:
            raise HTTPException(
                status_code=409, 
                detail="Pedido cancelado"
            )
        
        if payment["amount"] != event.amount or payment["currency"] != event.currency:
            raise HTTPException(
                status_code=409, 
                detail="Monto o moneda incorrectos"
            )
        
        cursor.execute("SELECT * FROM payment_events WHERE event_id=%s", (event.event_id,))
        previous = cursor.fetchone()
        if previous:
            if previous["payload_hash"] != digest:
                raise HTTPException(409, "Evento reutilizado con otros datos")
            
            return payment
        
        if payment["status"] != "PENDING" and payment["status"] != event.status:
            raise HTTPException(
                status_code=409, 
                detail="Pago ya finalizado"
            )
        
        cursor.execute("INSERT INTO payment_events VALUES (%s,%s,%s)", (event.event_id, digest, event.payment_id))
        cursor.execute("UPDATE payments SET status=%s WHERE id=%s", (event.status, event.payment_id))
        payment["status"] = event.status

        return payment


def mark_synchronized(payment_id):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("UPDATE payments SET synchronized=TRUE WHERE id=%s", (payment_id,))


def block_order(order_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT IGNORE INTO payment_orders(order_id) VALUES (%s)", (order_id,))
        cursor.execute("SELECT * FROM payment_orders WHERE order_id=%s FOR UPDATE", (order_id,))
        reference = cursor.fetchone()

        if reference["payment_id"]:
            cursor.execute("SELECT status FROM payments WHERE id=%s", (reference["payment_id"],))
            if cursor.fetchone()["status"] == "APPROVED":
                raise HTTPException(
                    status_code=409, 
                    detail="Pago confirmado: se requiere gestionar reembolso"
                )
            
        cursor.execute("UPDATE payment_orders SET cancelled=TRUE WHERE order_id=%s", (order_id,))


def refund_order(order_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM payment_orders WHERE order_id=%s FOR UPDATE", (order_id,))
        reference = cursor.fetchone()
        if not reference or not reference["payment_id"]:
            raise HTTPException(409, "No existe pago para reembolsar")
        
        cursor.execute("SELECT * FROM payments WHERE id=%s FOR UPDATE", (reference["payment_id"],))
        payment = cursor.fetchone()
        if payment["status"] not in ("APPROVED", "REFUNDED"):
            raise HTTPException(409, "El pago no está aprobado")
        
        cursor.execute("UPDATE payments SET status='REFUNDED' WHERE id=%s", (payment["id"],))
        cursor.execute("UPDATE payment_orders SET cancelled=TRUE WHERE order_id=%s", (order_id,))
