r"""Pruebas aisladas de Orders: sin .env, red ni MySQL reales.

Desde la raiz del proyecto:
backend\.venv\Scripts\python.exe -B -m unittest backend.tests.test_orders -v
"""
import hashlib
import json
import unittest
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, Mock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Evita que importar config lea archivos .env durante estas pruebas.
with patch("dotenv.load_dotenv", return_value=False):
    from backend.services.orders import main, db, config


class OrdersTests(unittest.TestCase):
    def setUp(self):
        config_patch = patch.multiple(
            config, INTERNAL_GATEWAY_SECRET="test-gateway",
            ORDERS_CLIENTS_SECRET="test-clients",
            ORDERS_INVENTORY_SECRET="test-inventory",
            ORDERS_PAYMENTS_SECRET="test-payments",
            PAYMENTS_ORDERS_SECRET="test-orders",
            CLIENTS_URL="http://clients.test", INVENTORY_URL="http://inventory.test",
            PAYMENTS_URL="http://payments.test",
            DB_USER="test", DB_PASS="test", DB_NAME="test",
        )
        config_patch.start()
        self.addCleanup(config_patch.stop)
        # Toda llamada externa debe simularse expresamente en cada prueba.
        for target in ("httpx.request", "httpx.post", "mysql.connector.connect"):
            guard = patch(target, side_effect=AssertionError("Acceso externo no simulado"))
            guard.start()
            self.addCleanup(guard.stop)
        self.client = TestClient(main.app, raise_server_exceptions=False)
        self.headers = {"X-Gateway-Secret": "test-gateway", "X-Authenticated-User": "1",
                        "X-Authenticated-Roles": "client"}
        self.admin = {**self.headers, "X-Authenticated-Roles": "admin"}
        self.body = {"items": [{"product_id": 1, "quantity": 2}], "delivery_method": "delivery"}
        self.user = {"id": 1, "admin": False}

    def row(self, **changes):
        return {"id": 1, "user_id": 1, "items": self.body["items"],
                "address_snapshot": {}, "status": "PENDING_PAYMENT", "payment_id": None,
                "total": 5000, "currency": "CLP", "delivery_method": "delivery", **changes}

    @contextmanager
    def sql_row(self, row):
        """Simula una fila SQL; ejecuta la logica real de db.py."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = row
        with patch.object(db, "connection") as connection:
            connection.return_value.__enter__.return_value = conn
            yield cursor

    def cancel_action(self, row, admin=False):
        args = [1, {"id": 1, "admin": admin}, "Cambio de planes"]
        with self.sql_row(row) as cursor:
            return db.cancel(*args), cursor

    def test_health(self):
        self.assertEqual(self.client.get("/health", headers=self.headers).status_code, 200)

    def test_gateway_and_identity_required(self):
        self.assertEqual(self.client.get("/orders").status_code, 403)
        for user_id in ("", "0", "-1", "abc"):
            with self.subTest(user_id=user_id):
                self.assertEqual(self.client.get("/orders", headers={**self.headers,
                    "X-Authenticated-User": user_id}).status_code, 401)

    def test_client_cannot_access_admin(self):
        for path in ("/admin/orders", "/admin/sales/report", "/admin/dispatch", "/admin/cash-registers"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=self.headers).status_code, 403)

    def test_list_filters_owner(self):
        with patch.object(db, "list_orders", return_value=[]) as query:
            self.assertEqual(self.client.get("/orders", headers=self.headers).status_code, 200)
            query.assert_called_once_with(1, 0, 50)

    def test_foreign_order_hidden_admin_allowed(self):
        with patch.object(db, "get_order", return_value=self.row(user_id=2)):
            self.assertEqual(self.client.get("/orders/1", headers=self.headers).status_code, 404)
            self.assertEqual(self.client.get("/orders/1", headers=self.admin).status_code, 200)

    def test_invalid_inputs(self):
        headers = {**self.headers, "Idempotency-Key": "order-123"}
        self.assertEqual(self.client.post("/orders", headers=self.headers, json=self.body).status_code, 422)
        for items in ([], self.body["items"] * 2, [{"product_id": 1, "quantity": 0}],
                      [{"product_id": 1, "quantity": True}]):
            with self.subTest(items=items):
                self.assertEqual(self.client.post("/orders", headers=headers,
                    json={**self.body, "items": items}).status_code, 422)

    def test_delivery_and_pickup(self):
        for method, profile, expected in (
            ("delivery", {"email_verified": True, "address": "Calle 123"}, 201),
            ("delivery", {"email_verified": True, "address": " "}, 409),
            ("pickup", {"email_verified": True}, 201),
            ("pickup", {"email_verified": False}, 409),
        ):
            with self.subTest(method=method, profile=profile), \
                 patch.object(main, "call_service", return_value=profile), \
                 patch.object(db, "begin_order", return_value={"id": 1}) as begin, \
                 patch.object(db, "finish_order", return_value=self.row()):
                response = self.client.post("/orders", headers={**self.headers,
                    "Idempotency-Key": "order-123"}, json={**self.body, "delivery_method": method})
                self.assertEqual(response.status_code, expected)
                if expected == 409:
                    begin.assert_not_called()

    def test_inventory_headers_and_errors(self):
        response = Mock(status_code=200, content=b"[]", json=lambda: [])
        with patch.object(main.httpx, "request", return_value=response) as send:
            main.reserve(1, self.body["items"])
            self.assertEqual(send.call_args.kwargs["headers"]["X-Service-Secret"], "test-inventory")
            self.assertNotIn("X-Gateway-Secret", send.call_args.kwargs["headers"])
        with patch.object(main.httpx, "request", side_effect=httpx.ConnectError("offline")):
            with self.assertRaises(HTTPException) as error:
                main.reserve(1, self.body["items"])
            self.assertEqual(error.exception.status_code, 503)

    def test_idempotency_conflict(self):
        with self.sql_row(self.row(request_hash="different")):
            with self.assertRaises(HTTPException) as error:
                db.begin_order(1, "order-123", self.body, {})
            self.assertEqual(error.exception.status_code, 409)

    def test_idempotency_same_payload(self):
        digest = hashlib.sha256(json.dumps(self.body, sort_keys=True).encode()).hexdigest()
        with self.sql_row(self.row(request_hash=digest)):
            self.assertEqual(db.begin_order(1, "order-123", self.body, {})["id"], 1)

    def test_finished_order_does_not_reserve_again(self):
        reserve = Mock()
        with patch.object(db, "get_order", return_value=self.row()):
            self.assertEqual(db.finish_order(1, reserve)["total"], 5000)
        reserve.assert_not_called()

    def test_creation_uses_inventory_prices(self):
        reserve = Mock(return_value=[{"product_id": 1, "quantity": 2, "price": 2500}])
        with patch.object(db, "get_order", return_value=self.row(status="CREATING")), \
             self.sql_row(self.row(status="CREATING")):
            result = db.finish_order(1, reserve)
            self.assertEqual((result["status"], result["total"]), ("PENDING_PAYMENT", 5000))

    def test_payment_wrong_amount_and_repeat(self):
        with self.sql_row(self.row()):
            with self.assertRaises(HTTPException) as error:
                db.mark_paid(1, 9, 1)
            self.assertEqual(error.exception.status_code, 409)
        with self.sql_row(self.row(status="PAID", payment_id=9)) as cursor:
            db.mark_paid(1, 9, 5000)
            self.assertFalse(any(call.args[0].startswith("UPDATE ") for call in cursor.execute.call_args_list))

    def test_transitions(self):
        with self.sql_row(self.row()):
            with self.assertRaises(HTTPException):
                db.advance(1, "PREPARING")
        with self.sql_row(self.row(status="READY", delivery_method="pickup")) as cursor:
            db.advance(1, "DELIVERED")
            self.assertEqual(cursor.execute.call_args.args[1], ("DELIVERED", 1))

    def test_internal_paid_secret(self):
        with patch.object(db, "mark_paid") as mark:
            data = {"payment_id": 9, "amount": 5000}
            self.assertEqual(self.client.post("/internal/orders/1/paid", json=data).status_code, 403)
            self.assertEqual(self.client.post("/internal/orders/1/paid", json=data,
                headers={"X-Service-Secret": "test-orders"}).status_code, 200)
            mark.assert_called_once_with(1, 9, 5000)

    def test_cancel_endpoint_calls_db_correctly(self):
        with self.sql_row(self.row(status="CANCELLED")), patch.object(db, "get_order", return_value=self.row(status="CANCELLED")):
            result = self.client.post("/orders/1/cancel", headers=self.headers, json={"reason": "Cambio de planes"})
            self.assertEqual(result.status_code, 200, result.text)

    def test_pending_cancellation_releases_stock(self):
        action, _ = self.cancel_action(self.row())
        self.assertEqual(action, "release")

    def test_paid_admin_cancellation_refunds(self):
        action, _ = self.cancel_action(self.row(status="PAID", payment_id=9), admin=True)
        self.assertEqual(action, "refund")

    def test_paid_client_only_requests_cancellation(self):
        action, _ = self.cancel_action(self.row(status="PAID", payment_id=9))
        self.assertEqual(action, "requested")

    def test_cancellation_sql_column_exists(self):
        # Incluye la solicitud del cliente sobre un pedido ya pagado.
        for status, payment_id in (("PENDING_PAYMENT", None), ("PAID", 9)):
            with self.subTest(status=status):
                _, cursor = self.cancel_action(self.row(status=status, payment_id=payment_id))
                updates = [c.args[0] for c in cursor.execute.call_args_list if c.args[0].startswith("UPDATE")]
                self.assertTrue(updates)
                for sql in updates:
                    self.assertIn("cancellation_reason", sql)
                    self.assertNotIn("canellation_reason", sql)

    def test_cancellation_retry_actions(self):
        for row, admin, expected in (
            (self.row(status="CANCELLED"), False, "done"),
            (self.row(status="CANCELLING"), False, "release"),
            (self.row(status="CANCELLING", payment_id=9), True, "refund"),
            (self.row(status="CANCELLING", payment_id=9), False, "requested"),
        ):
            with self.subTest(row=row, admin=admin):
                self.assertEqual(self.cancel_action(row, admin)[0], expected)

    def test_failed_release_does_not_finish_cancellation(self):
        with patch.object(db, "cancel", return_value="release"), \
             patch.object(main, "release", side_effect=HTTPException(503, "offline")), \
             patch.object(db, "finish_cancellation") as finish:
            response = self.client.post("/orders/1/cancel", headers=self.headers, json={"reason": "Cambio de planes"})
            self.assertEqual(response.status_code, 503)
            finish.assert_not_called()

    def test_release_blocks_payments_before_inventory(self):
        with patch.object(main, "call_service", side_effect=HTTPException(409, "Paid")) as call:
            with self.assertRaises(HTTPException):
                main.release(1)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.args[0], "PAYMENTS")

    def test_receipt_failure_not_marked_sent(self):
        with patch.object(main.httpx, "post", side_effect=httpx.ConnectError("offline")), \
             patch.object(db, "mark_receipt_sent") as mark:
            with self.assertRaises(HTTPException):
                main.send_receipt({"id": 1, "receipt_sent": False, "receipt": {}}, 1)
            mark.assert_not_called()

    def test_html_escapes_content(self):
        result = main.printable("<script>", "<img>", [{"name": "<b>", "quantity": 1, "price": 1}])
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;b&gt;", result)

    def test_report_dates(self):
        with self.assertRaises(HTTPException) as error:
            db.sales_report(date(2026, 11, 23), date(2026, 11, 1))
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
