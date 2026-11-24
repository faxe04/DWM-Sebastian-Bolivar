from contextlib import contextmanager
from pathlib import Path
import mysql.connector
from .import config
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException


FIELDS = ("full_name", "email", "phone", "address")


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
        autocommit=False)
    
    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_client(user_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM clients WHERE user_id=%s AND active=TRUE", (user_id,))
        return cursor.fetchone()


def save_client(user_id, values, create=False):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM clients WHERE user_id=%s FOR UPDATE", (user_id,))
        previous = cursor.fetchone()
        if create:
            if previous:
                raise HTTPException(409, "El perfil ya existe")
            
            cursor.execute(
                "INSERT INTO clients (user_id, full_name, email, phone, address) VALUES (%s, %s, %s, %s, %s)",
                (user_id,values["full_name"], values["email"], values["phone"], values["address"]
            )
        )

        else:
            if not previous or not previous["active"]:
                raise HTTPException(404, "Cliente no encontrado")
            
            cursor.execute("UPDATE clients SET " + ",".join(f + "=%s" for f in FIELDS) + " WHERE user_id=%s", (*(values[f] for f in FIELDS), user_id))
            if previous["email"] != values["email"]:
                cursor.execute("UPDATE clients SET email_verified=FALSE WHERE user_id=%s", (user_id,))
                cursor.execute("DELETE FROM email_tokens WHERE user_id=%s", (user_id,))

        cursor.execute("SELECT * FROM clients WHERE user_id=%s", (user_id,))
        return cursor.fetchone()


def list_clients(skip, limit):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM clients WHERE active=TRUE ORDER BY user_id LIMIT %s OFFSET %s", (limit, skip))
        return cursor.fetchall()


def deactivate(user_id):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("UPDATE clients SET active=FALSE WHERE user_id=%s AND active=TRUE", (user_id,))
        return cursor.rowcount


def approve_address(user_id, latitude, longitude):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT user_id FROM clients WHERE user_id=%s AND active=TRUE FOR UPDATE", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404, 
                detail="Cliente no encontrado"
            )
        cursor.execute("UPDATE clients SET latitude=%s,longitude=%s,address_verified=TRUE WHERE user_id=%s", (latitude, longitude, user_id))


def send_verification(user_id):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT email FROM clients WHERE user_id=%s AND active=TRUE FOR UPDATE", (user_id,))
        client = cursor.fetchone()
        if not client:
            raise HTTPException(
                status_code=404, 
                detail="Cliente no encontrado"
            )
        
        cursor.execute("DELETE FROM email_tokens WHERE user_id=%s", (user_id,))
        cursor.execute("INSERT INTO email_tokens VALUES (%s,%s,%s,%s)", (digest, user_id, client["email"], expires))
        cursor.execute("INSERT INTO mail_outbox(user_id,recipient,message) VALUES (%s,%s,%s)", (user_id, client["email"], "DEMO. Token para POST /api/v1/clients/verify-email: " + token))


def verify_email(token):
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT user_id FROM email_tokens WHERE token_hash=%s", (digest,))
        reference = cursor.fetchone()
        if not reference:
            raise HTTPException(
                status_code=400, 
                detail="Token inválido o utilizado"
            )
        
        cursor.execute("SELECT * FROM clients WHERE user_id=%s FOR UPDATE", (reference["user_id"],))
        client = cursor.fetchone()
        cursor.execute("SELECT * FROM email_tokens WHERE token_hash=%s FOR UPDATE", (digest,))
        row = cursor.fetchone()
        if not row or row["expires_at"] <= datetime.now(timezone.utc).replace(tzinfo=None) or not client["active"] or row["email"] != client["email"]:
            raise HTTPException(400, "Token inválido o expirado")
        
        cursor.execute("UPDATE clients SET email_verified=TRUE WHERE user_id=%s", (client["user_id"],))
        cursor.execute("DELETE FROM email_tokens WHERE user_id=%s", (client["user_id"],))


def mailbox():
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM mail_outbox ORDER BY id DESC LIMIT 50")
        return cursor.fetchall()


def queue_receipt(user_id, sale_id, message):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT email, active, email_verified FROM clients WHERE user_id=%s FOR UPDATE", (user_id,))

        client = cursor.fetchone()

        if not client or not client["active"] or not client["email_verified"]:
            raise HTTPException(
                status_code=409,
                detail="Cliente activo con correo verificado requerido"
            )

        cursor.execute("SELECT mail_id FROM receipt_deliveries WHERE sale_id=%s",(sale_id,))

        previous = cursor.fetchone()

        if previous:
            return previous["mail_id"]

        cursor.execute("INSERT INTO mail_outbox(user_id, recipient, message) VALUES (%s, %s, %s)",(user_id, client["email"], message))

        mail_id = cursor.lastrowid
        cursor.execute("INSERT INTO receipt_deliveries(sale_id, mail_id) VALUES (%s, %s)",(sale_id, mail_id))

        return mail_id