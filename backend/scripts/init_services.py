"""Crea las bases de cada servicio; la cuenta root solo se usa en la preparación."""
import os
from pathlib import Path
import mysql.connector

def main():
    secret_dir = Path(os.getenv("SECRET_DIR", "/run/secrets"))
    scripts = Path(__file__).resolve().parents[1] / "infrastructure" / "mysql"
    conn = mysql.connector.connect(host=os.getenv("DB_HOST", "mysql"), port=int(os.getenv("DB_PORT", "3306")),
        user="root", password=(secret_dir / "mysql_root_password").read_text().strip())
    try:
        with conn.cursor() as cursor:
            for name, filename in (("clients", "003_clients.sql"), ("orders", "004_orders.sql"), ("payments", "005_payments.sql")):
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {name} CHARACTER SET utf8mb4")
                cursor.execute(f"CREATE USER IF NOT EXISTS '{name}_app'@'%' IDENTIFIED BY %s", ((secret_dir / (name + "_db_password")).read_text().strip(),))
                cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {name}.* TO '{name}_app'@'%'")
                cursor.execute("USE " + name)
                for statement in (scripts / filename).read_text().split(";"):
                    if statement.strip():
                        cursor.execute(statement)
            cursor.execute("USE inventory")
            for statement in (scripts / "006_reservations.sql").read_text().split(";"):
                if statement.strip():
                    cursor.execute(statement)
            for database, filename in (("orders", "007_sales.sql"), ("clients", "008_receipt_mail.sql")):
                cursor.execute("USE " + database)
                for statement in (scripts / filename).read_text().split(";"):
                    if statement.strip():
                        cursor.execute(statement)
        conn.commit()
        print("Bases de clientes, pedidos, pagos y reservas preparadas.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
