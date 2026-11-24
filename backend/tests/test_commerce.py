import hashlib
import hmac
import json
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
with patch("dotenv.load_dotenv", return_value=False):
    from backend.services.payments import main as payments
    from backend.services.orders import main as orders
    from backend.services.clients.schemas import ClientInput

class CommerceTests(unittest.TestCase):
    def test_payment_signature_required_before_database(self):
        with patch.object(payments.config, "PAYMENT_WEBHOOK_SECRET", "test"), patch.object(payments.db, "apply_event") as apply:
            with self.assertRaises(HTTPException) as caught:
                payments.process_event(b"{}", "bad")
            self.assertEqual(caught.exception.status_code, 403)
            apply.assert_not_called()

    def test_approved_payment_updates_order(self):
        event = {"event_id": "event-123", "payment_id": 1, "amount": 3500, "currency": "CLP", "status": "APPROVED"}
        raw = json.dumps(event).encode()
        signature = hmac.new(b"test", raw, hashlib.sha256).hexdigest()
        payment = {"id": 1, "order_id": 2, "amount": 3500, "status": "APPROVED", "synchronized": False}
        with patch.object(payments.config, "PAYMENT_WEBHOOK_SECRET", "test"), patch.object(payments.db, "apply_event", return_value=payment), patch.object(payments, "orders_request") as send, patch.object(payments.db, "mark_synchronized") as mark:
            payments.process_event(raw, signature)
            send.assert_called_once_with("POST", "/internal/orders/2/paid", {"payment_id": 1, "amount": 3500})
            mark.assert_called_once_with(1)

    def test_failed_order_sync_remains_retryable(self):
        raw = json.dumps({"event_id": "event-123", "payment_id": 1, "amount": 3500, "currency": "CLP", "status": "APPROVED"}).encode()
        signature = hmac.new(b"test", raw, hashlib.sha256).hexdigest()
        payment = {"id": 1, "order_id": 2, "amount": 3500, "status": "APPROVED", "synchronized": False}
        with patch.object(payments.config, "PAYMENT_WEBHOOK_SECRET", "test"), patch.object(payments.db, "apply_event", return_value=payment), patch.object(payments, "orders_request", side_effect=HTTPException(503)), patch.object(payments.db, "mark_synchronized") as mark:
            with self.assertRaises(HTTPException):
                payments.process_event(raw, signature)
            mark.assert_not_called()

    def test_dummy_disabled_by_default(self):
        with patch.object(payments.config, "DEMO_MODE", False):
            with self.assertRaises(HTTPException):
                payments.demo_only()

    def test_client_cannot_simulate_payment(self):
        with patch.multiple(payments.config, INTERNAL_GATEWAY_SECRET="test", DEMO_MODE=True):
            with TestClient(payments.app) as client:
                result = client.post("/admin/payments/1/simulate", json={"result": "APPROVED"}, headers={
                    "X-Gateway-Secret": "test", "X-Authenticated-User": "1", "X-Authenticated-Roles": "client"})
                self.assertEqual(result.status_code, 403)

    def test_delivery_requires_only_address(self):
        orders.validate_delivery({"address": "Calle 123"})
        for address in (None, "", "   "):
            with self.subTest(address=address), self.assertRaises(HTTPException):
                orders.validate_delivery({"address": address})

    def test_current_client_fields(self):
        profile = ClientInput(full_name="Cliente Test", email="TEST@example.com",
                              phone="900000000", address="Calle 123")
        self.assertEqual(profile.email, "test@example.com")
        self.assertEqual(set(profile.model_dump()), {"full_name", "email", "phone", "address"})
        with self.assertRaises(ValueError):
            ClientInput(**profile.model_dump(), latitude=0)

    def test_other_client_cannot_read_order(self):
        with patch.object(orders.db, "get_order", return_value={"user_id": 3}):
            with self.assertRaises(HTTPException) as caught:
                orders.owned(1, {"id": 2, "admin": False})
            self.assertEqual(caught.exception.status_code, 404)
