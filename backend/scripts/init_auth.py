"""Preparación local idempotente: base Auth y dos cuentas ficticias de prueba."""
import os
from pathlib import Path
import mysql.connector
from backend.auth.security import hash_password


def secret(name):
    return (Path("/run/secrets") / name).read_text().strip()


def main():
    conn = mysql.connector.connect(host=os.getenv("DB_HOST", "mysql"), user="root",
                                  password=secret("mysql_root_password"), connection_timeout=5)
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS auth CHARACTER SET utf8mb4")
            cursor.execute("CREATE USER IF NOT EXISTS 'auth_app'@'%' IDENTIFIED BY %s", (secret("auth_db_password"),))
            cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON auth.* TO 'auth_app'@'%'")
            cursor.execute("USE auth")
            for statement in Path("/app/backend/infrastructure/mysql/002_auth.sql").read_text().split(";"):
                if statement.strip():
                    cursor.execute(statement)
            for username, role, password_file in [("admin-demo", "admin", "demo_admin_password"), ("cliente-demo", "client", "demo_client_password")]:
                cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
                if cursor.fetchone() is None:
                    cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                                   (username, hash_password(secret(password_file)), role))
        conn.commit()
        print("Auth preparado. Se conservaron cuentas existentes; no se imprimieron credenciales.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
