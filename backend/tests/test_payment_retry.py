r"""Secuencia REJECTED -> nuevo intento -> APPROVED -> Orders PAID.

Ejecutar desde la raiz:
backend\.venv\Scripts\python.exe -B -m unittest backend.tests.test_payment_retry -v

Ejecuta endpoints y funciones db reales, con SQLite temporal en memoria.
No lee .env ni conecta a MySQL. No prueba bloqueos/concurrencia de MySQL.
"""
from contextlib import contextmanager
import sqlite3
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

with patch("dotenv.load_dotenv", return_value=False):
    from backend.services.payments import main as payments
    from backend.services.orders import main as orders


class TemporaryCursor:
    """Adapta solamente la sintaxis MySQL usada por esta secuencia."""
    def __init__(self, database):
        self.cursor = database.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()

    def execute(self, sql, values=()):
        sql = sql.replace("%s", "?").replace(" FOR UPDATE", "")
        sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
        self.cursor.execute(sql, values)

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None


class TemporaryConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self, dictionary=False):
        return TemporaryCursor(self.database)

    @contextmanager
    def connection(self):
        with self.database:
            yield self


class PaymentRetryTests(unittest.TestCase):
    def test_rejected_then_new_payment_approved(self):
        database = sqlite3.connect(":memory:", check_same_thread=False)
        database.row_factory = sqlite3.Row
        self.addCleanup(database.close)
        # Columnas y restricciones relevantes de 004_orders.sql y 005_payments.sql.
        database.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                total INTEGER NOT NULL, currency TEXT NOT NULL,
                status TEXT NOT NULL, payment_id INTEGER,
                items TEXT NOT NULL, address_snapshot TEXT NOT NULL
            );
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                request_key TEXT NOT NULL, amount INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CLP',
                status TEXT NOT NULL DEFAULT 'PENDING',
                synchronized INTEGER NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, request_key)
            );
            CREATE TABLE payment_events (
                event_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
                payment_id INTEGER NOT NULL REFERENCES payments(id)
            );
            CREATE TABLE payment_orders (
                order_id INTEGER PRIMARY KEY,
                cancelled INTEGER NOT NULL DEFAULT FALSE, payment_id INTEGER
            );
            INSERT INTO orders VALUES (1, 1, 5000, 'CLP', 'PENDING_PAYMENT', NULL, '[]', '{}');
        """)
        temporary = TemporaryConnection(database)
        for target in (payments.db, orders.db):
            replacement = patch.object(target, "connection", temporary.connection)
            replacement.start()
            self.addCleanup(replacement.stop)
        for config in (payments.config, orders.config):
            replacement = patch.multiple(config,
                INTERNAL_GATEWAY_SECRET="test-gateway",
                PAYMENTS_ORDERS_SECRET="test-payments-orders")
            replacement.start()
            self.addCleanup(replacement.stop)

        client_headers = {"X-Gateway-Secret": "test-gateway",
                          "X-Authenticated-User": "1", "X-Authenticated-Roles": "client"}
        admin_headers = {**client_headers, "X-Authenticated-Roles": "admin"}
        orders_client = TestClient(orders.app)
        payments_client = TestClient(payments.app)

        def local_request(method, url, **kwargs):
            # Ejecuta el endpoint real de Orders, incluidas sus claves y SQL.
            parsed = urlsplit(url)
            self.assertEqual(parsed.netloc, "orders.test")
            return orders_client.request(method, parsed.path,
                headers=kwargs.get("headers"), json=kwargs.get("json"))

        def create(key):
            response = payments_client.post("/payments", json={"order_id": 1},
                headers={**client_headers, "Idempotency-Key": key})
            self.assertEqual(response.status_code, 201, response.text)
            self.assertFalse(response.json()["real_charge"])
            return response.json()

        def simulate(payment_id, result):
            response = payments_client.post(f"/admin/payments/{payment_id}/simulate",
                headers=admin_headers, json={"result": result})
            self.assertEqual(response.status_code, 200, response.text)

        def read_payment(payment_id):
            response = payments_client.get(f"/payments/{payment_id}", headers=client_headers)
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()

        def read_order():
            response = orders_client.get("/orders/1", headers=client_headers)
            self.assertEqual(response.status_code, 200, response.text)
            return response.json()

        with patch.multiple(payments.config, DEMO_MODE=True,
                            PAYMENT_WEBHOOK_SECRET="test-signature", ORDERS_URL="http://orders.test"), \
             patch("httpx.request", side_effect=local_request), \
             patch("mysql.connector.connect", side_effect=AssertionError("MySQL real no permitido")):
            first = create("pago-001")
            self.assertEqual(first["status"], "PENDING")
            print(f"pago-001: payment_id={first['id']}, PENDING")

            simulate(first["id"], "REJECTED")
            self.assertEqual(read_payment(first["id"])["status"], "REJECTED")
            self.assertEqual(read_order()["status"], "PENDING_PAYMENT")
            print("REJECTED: Orders sigue PENDING_PAYMENT")

            second = create("pago-002")
            self.assertNotEqual(second["id"], first["id"])
            self.assertEqual(second["status"], "PENDING")
            print(f"pago-002: payment_id={second['id']}, PENDING (otro ID)")

            simulate(second["id"], "APPROVED")
            self.assertEqual(read_payment(second["id"])["status"], "APPROVED")
            self.assertTrue(read_payment(second["id"])["synchronized"])
            order = read_order()
            self.assertEqual(order["status"], "PAID")
            self.assertEqual(order["payment_id"], second["id"])
            print(f"APPROVED: Orders PAID, payment_id={order['payment_id']}")

            # Repetir claves/eventos conserva los intentos y la confirmacion.
            self.assertEqual(create("pago-001")["id"], first["id"])
            self.assertEqual(create("pago-002")["id"], second["id"])
            simulate(second["id"], "APPROVED")
            self.assertEqual(database.execute("SELECT COUNT(*) FROM payments").fetchone()[0], 2)
            self.assertEqual(database.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0], 2)
            self.assertEqual(read_order()["payment_id"], second["id"])
            print("Reintentos: siguen siendo 2 pagos y 2 eventos")


if __name__ == "__main__":
    unittest.main()
