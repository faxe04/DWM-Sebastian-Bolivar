import unittest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
with patch("dotenv.load_dotenv", return_value=False):
    from backend.auth.main import app as auth_app
    from backend.auth import config
    from backend.auth.db import _protect_last_admin as protect_last_admin
    from backend.services.orders.main import printable
    from backend.request_logging import install
from fastapi import FastAPI

class CompletionTests(unittest.TestCase):
    def test_last_admin_cannot_be_disabled(self):
        cursor = Mock()
        cursor.fetchall.return_value = [{"id": 1}]
        with self.assertRaises(HTTPException) as caught:
            protect_last_admin(cursor, 1, False)
        self.assertEqual(caught.exception.status_code, 409)
        protect_last_admin(cursor, 1, True)

    def test_client_cannot_manage_users(self):
        with patch.object(config, "AUTH_INTROSPECTION_SECRET", "test"), TestClient(auth_app) as client:
            response = client.get("/admin/users", headers={"X-Gateway-Auth-Secret":"test",
                "X-Authenticated-User":"1", "X-Authenticated-Roles":"client"})
            self.assertEqual(response.status_code, 403)

    def test_internal_account_lookup_rejects_unknown_component(self):
        with patch.object(config, "CLIENTS_AUTH_SECRET", "test"), TestClient(auth_app) as client:
            self.assertEqual(client.get("/internal/users/1").status_code, 403)

    def test_printable_escapes_customer_and_product_html(self):
        html = printable("Boleta", "<script>x</script>", [{"name":"<img onerror=x>", "quantity":1, "price":100}])
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img ", html)
        self.assertIn("&lt;script&gt;", html)

    def test_request_id_is_preserved_without_logging_private_data(self):
        app = FastAPI()
        @app.get("/test")
        def test_route():
            return {"ok": True}
        install(app)
        with patch("backend.request_logging.logging.getLogger") as logger, TestClient(app) as client:
            response = client.get("/test?private=do-not-log", headers={"X-Request-ID":"demo-123", "Authorization":"Bearer private-token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["x-request-id"], "demo-123")
            recorded = logger.return_value.info.call_args.args[0]
            self.assertIn("demo-123", recorded)
            self.assertNotIn("do-not-log", recorded)
            self.assertNotIn("private-token", recorded)
