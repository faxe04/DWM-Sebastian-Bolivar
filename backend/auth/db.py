from contextlib import contextmanager
import mysql.connector
from fastapi import HTTPException
from . import config


@contextmanager
def connection():
    if not config.DB_USER:
        raise RuntimeError("DB_USER no esta configurado en .env")
    
    if not config.DB_PASS:
        raise RuntimeError("DB_PASS no esta configurado en .env")

    if not config.DB_NAME:
        raise RuntimeError("DB_NAME no está configurado")
    
    conn = mysql.connector.connect(
        host=config.DB_HOST, 
        port=config.DB_PORT, 
        user=config.DB_USER, 
        password=config.DB_PASS, 
        database=config.DB_NAME, 
        connection_timeout=5, 
        autocommit=False
    )
    
    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_user(username):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT id, username, password_hash, role, enabled FROM users WHERE username=%s", (username,))
        return cursor.fetchone()


def register(username, password_hash):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("INSERT INTO users(username,password_hash,role) VALUES (%s,%s,'client')", (username, password_hash))
        return {"id": cursor.lastrowid, "username": username, "role": "client"}


def create_session(token_hash, user_id, expires_at):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)", (token_hash, user_id, expires_at))


def get_session(token_hash):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT u.id AS user_id, u.username, u.role, s.expires_at "
            "FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=%s AND s.expires_at > UTC_TIMESTAMP() AND u.enabled=TRUE", (token_hash,))
        return cursor.fetchone()


def delete_session(token_hash):
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("DELETE FROM sessions WHERE token_hash=%s", (token_hash,))


# ===== USERS =====
def _public_user(cursor, user_id):
    cursor.execute(
        "SELECT id, username, role, enabled FROM users WHERE id=%s",
        (user_id,)
    )
    user = cursor.fetchone()

    if user is None:
        raise HTTPException(404, "Usuario no encontrado")

    return user


def list_users(skip, limit):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT id, username, role, enabled FROM users "
            "ORDER BY id LIMIT %s OFFSET %s",
            (limit, skip)
        )
        return cursor.fetchall()


def get_public_user(user_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        return _public_user(cursor, user_id)


def create_admin_user(username, password_hash, role, enabled):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        cursor.execute(
            "INSERT INTO users(username, password_hash, role, enabled) "
            "VALUES (%s, %s, %s, %s)",
            (username, password_hash, role, enabled)
        )
        return _public_user(cursor, cursor.lastrowid)


# ===== MODS =====
def _protect_last_admin(cursor, user_id, will_be_admin):
    cursor.execute(
        "SELECT id FROM users "
        "WHERE role='admin' AND enabled=TRUE "
        "ORDER BY id FOR UPDATE"
    )
    admins = [row["id"] for row in cursor.fetchall()]

    if user_id in admins and len(admins) == 1 and not will_be_admin:
        raise HTTPException(
            409, "Debe quedar al menos un administrador activo"
        )


def update_user(user_id, username, role, enabled, password_hash=None):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        _protect_last_admin(
            cursor, user_id, role == "admin" and enabled
        )
        _public_user(cursor, user_id)

        cursor.execute(
            "UPDATE users SET username=%s, role=%s, enabled=%s "
            "WHERE id=%s",
            (username, role, enabled, user_id)
        )

        if password_hash is not None:
            cursor.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (password_hash, user_id)
            )

        cursor.execute(
            "DELETE FROM sessions WHERE user_id=%s",
            (user_id,)
        )

        return _public_user(cursor, user_id)


def disable_user(user_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        _protect_last_admin(cursor, user_id, False)
        _public_user(cursor, user_id)

        cursor.execute(
            "UPDATE users SET enabled=FALSE WHERE id=%s",
            (user_id,)
        )
        cursor.execute(
            "DELETE FROM sessions WHERE user_id=%s",
            (user_id,)
        )


# ===== Interla Comunication =====
def account_for_profile(user_id):
    with connection() as conn, conn.cursor(dictionary=True) as cursor:
        user = _public_user(cursor, user_id)

        if not user["enabled"]:
            raise HTTPException(409, "Cuenta deshabilitada")

        return {
            "id": user["id"],
            "enabled": user["enabled"]
        }

