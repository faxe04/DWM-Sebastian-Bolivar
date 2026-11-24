from contextlib import contextmanager
import mysql.connector
from . import config
import json
import hashlib
from fastapi import HTTPException


PRODUCT_COLUMNS = "id, name, description, category, price, stock, available, featured"


@contextmanager
def connection():
    if not config.DB_USER:
        raise RuntimeError("DB_USER no esta configurado")
    
    if not config.DB_PASS:
        raise RuntimeError("DB_PASS no esta configurado")

    if not config.DB_NAME:
        raise RuntimeError("DB_NAME no está configurado")
    
    conn = mysql.connector.connect(
        host=config.DB_HOST, 
        port=config.DB_PORT, 
        user=config.DB_USER, 
        password=config.DB_PASS,
        database=config.DB_NAME, 
        connection_timeout=5, 
        autocommit=False, 
        charset="utf8mb4",
    )
    
    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def list_products(q=None, skip=0, limit=50, category=None, available=None, featured=None):
    conditions = ["is_active = TRUE"]
    values = []
    if q:
        conditions.append("LOCATE(%s, name) > 0")
        values.append(q)

    if category is not None:
        conditions.append("category = %s")
        values.append(category)

    if available is not None:
        conditions.append("(available = TRUE AND stock > 0) = %s")
        values.append(available)

    if featured is not None:
        conditions.append("featured = %s")
        values.append(featured)

    sql = "SELECT " + PRODUCT_COLUMNS + " FROM products WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id LIMIT %s OFFSET %s"

    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute(sql, (*values, limit, skip))
        return cursor.fetchall()


def get_product(product_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT " + PRODUCT_COLUMNS + " FROM products WHERE id=%s AND is_active=TRUE", (product_id,))
        return cursor.fetchone()


def create_product(product):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO products (name, description, category, price, stock, available, featured) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                product["name"], 
                product["description"], 
                product["category"], 
                product["price"],
                product["stock"], 
                product["available"], 
                product["featured"]),
        )
        return {"id": cursor.lastrowid, **product}


def update_product(product_id, product):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM products WHERE id=%s AND is_active=TRUE FOR UPDATE", (product_id,))
        if cursor.fetchone() is None:
            return None
        
        cursor.execute(
            "UPDATE products SET name=%s, description=%s, category=%s, price=%s, stock=%s, "
            "available=%s, featured=%s WHERE id=%s",
            (
                product["name"], 
                product["description"], 
                product["category"], 
                product["price"],
                product["stock"], 
                product["available"], 
                product["featured"], 
                product_id
             ),
        )

        return {"id": product_id, **product}


def delete_product(product_id):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("UPDATE products SET is_active=FALSE WHERE id=%s AND is_active=TRUE", (product_id,))
        return cursor.rowcount > 0


def reserve(order_id, requested):
    fingerprint = hashlib.sha256(json.dumps(requested, sort_keys=True).encode()).hexdigest()

    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT IGNORE INTO reservations(order_id,request_hash,status,items) VALUES (%s,%s,'CREATING','[]')", (order_id, fingerprint))
        cursor.execute("SELECT * FROM reservations WHERE order_id=%s FOR UPDATE", (order_id,))
        previous = cursor.fetchone()
        if previous["request_hash"] != fingerprint:
            raise HTTPException(
                status_code=409, 
                detail="Reserva diferente para el mismo pedido"
            )
        
        if previous["status"] == "RELEASED":
            raise HTTPException(
                status_code=409, 
                detail="Reserva cancelada"
            )
        
        if previous["status"] == "ACTIVE":
            return json.loads(previous["items"])
        
        items = []
        for item in sorted(requested, key=lambda x: x["product_id"]):
            cursor.execute("SELECT * FROM products WHERE id=%s FOR UPDATE", (item["product_id"],))
            product = cursor.fetchone()
            if not product or not product["is_active"] or not product["available"] or product["stock"] < item["quantity"]:
                raise HTTPException(
                    status_code=409, detail="Producto no disponible o stock insuficiente"
                )
            
            cursor.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (item["quantity"], item["product_id"]))
            items.append({**item, "name": product["name"], "price": product["price"]})

        cursor.execute("UPDATE reservations SET status='ACTIVE',items=%s WHERE order_id=%s", (json.dumps(items), order_id))
        return items
    

def release(order_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT IGNORE INTO reservations(order_id,request_hash,status,items) VALUES (%s,'','RELEASED','[]')", (order_id,))
        cursor.execute("SELECT * FROM reservations WHERE order_id=%s FOR UPDATE", (order_id,))
        row = cursor.fetchone()
        if not row or row["status"] == "RELEASED":
            return
        
        for item in sorted(json.loads(row["items"]), key=lambda x: x["product_id"]):
            cursor.execute("UPDATE products SET stock=stock+%s WHERE id=%s", (item["quantity"], item["product_id"]))
            
        cursor.execute("UPDATE reservations SET status='RELEASED' WHERE order_id=%s", (order_id,))
