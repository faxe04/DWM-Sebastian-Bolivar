import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
with patch("dotenv.load_dotenv", return_value=False):
    from backend.gateway import config, gateway, security


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.roles = ["admin"]
        self.active = True
        self.failure = None
        self.upstream_status = 200
        real_client = httpx.AsyncClient
        patches = [patch.object(config, "VAULT_ADDR", "http://vault"),
                   patch.object(config, "AUTH_SERVICE_URL", "http://auth"),
                   patch.object(config, "ROUTES", {"inventory": "http://inventory"}),
                   patch.object(config, "VAULT_TOKEN", "test-vault"),
                   patch.object(security.httpx, "AsyncClient", side_effect=lambda **kw: real_client(transport=httpx.MockTransport(self.respond), **kw))]
        for replacement in patches:
            replacement.start()
            self.addCleanup(replacement.stop)
        self.client = TestClient(gateway.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def respond(self, request):
        self.seen.append(request)
        if request.url.host == self.failure:
            raise httpx.ConnectError("secret connection details", request=request)
        if request.url.host == "vault":
            self.assertEqual(request.headers["X-Vault-Token"], "test-vault")
            return httpx.Response(200, json={"data": {"data": {"inventory_gateway_secret": "test-inventory", "auth_introspection_secret": "test-auth"}}})
        if request.url.host == "auth":
            self.assertEqual(request.headers["X-Gateway-Auth-Secret"], "test-auth")
            if request.url.path == "/login":
                return httpx.Response(200, json={"access_token": "test-session", "token_type": "bearer", "expires_in": 900})
            if request.url.path == "/logout":
                return httpx.Response(200, json={"message": "Sesión finalizada"})
            return httpx.Response(200, json={"active": self.active, "user_id": "7", "username": "cliente", "roles": self.roles})
        self.assertEqual(request.headers["X-Gateway-Secret"], "test-inventory")
        return httpx.Response(self.upstream_status, json={"result": "ok"})

    def test_public_catalog_does_not_need_auth(self):
        response = self.client.get("/api/v1/products?category=cafe")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("auth", [r.url.host for r in self.seen])
        self.assertEqual(self.seen[-1].url.params["category"], "cafe")

    def test_external_identity_and_secret_are_not_forwarded(self):
        response = self.client.get("/api/v1/products", headers={"X-Authenticated-Roles": "admin", "X-Authenticated-User": "fake", "X-Gateway-Secret": "fake"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Authenticated-Roles", self.seen[-1].headers)
        self.assertNotIn("X-Authenticated-User", self.seen[-1].headers)

    def test_admin_uses_verified_identity(self):
        response = self.client.post("/api/v1/admin/products", json={"name": "Latte"}, headers={"Authorization": "Bearer session", "X-Authenticated-User": "fake"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.seen[-1].headers["X-Authenticated-User"], "7")
        self.assertNotIn("Authorization", self.seen[-1].headers)

    def test_missing_session_stops_before_dependencies(self):
        self.assertEqual(self.client.post("/api/v1/admin/products", json={}).status_code, 401)
        self.assertEqual(self.seen, [])

    def test_customer_cannot_escalate_role_with_header(self):
        self.roles = ["client"]
        response = self.client.post("/api/v1/admin/products", json={}, headers={"Authorization": "Bearer session", "X-Authenticated-Roles": "admin"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("inventory", [r.url.host for r in self.seen])

    def test_expired_session(self):
        self.active = False
        self.assertEqual(self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer session"}).status_code, 401)

    def test_unknown_routes_and_methods_do_not_reach_services(self):
        for route, method, expected in [("internal/reservations", "GET", 404), ("products", "POST", 405), ("admin/products/1", "PATCH", 405), ("products/0", "GET", 422)]:
            self.assertEqual(self.client.request(method, "/api/v1/" + route).status_code, expected)
        self.assertEqual(self.seen, [])

    def test_vault_failure_is_controlled(self):
        self.failure = "vault"
        response = self.client.get("/api/v1/products")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret connection", response.text)

    def test_auth_failure_does_not_grant_access(self):
        self.failure = "auth"
        response = self.client.get("/api/v1/admin/products", headers={"Authorization": "Bearer session"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("inventory", [r.url.host for r in self.seen])

    def test_upstream_errors_are_not_exposed(self):
        self.upstream_status = 500
        response = self.client.get("/api/v1/products")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("result", response.text)

    def test_oversized_body_is_rejected(self):
        response = self.client.post("/api/v1/admin/products", content="x" * 65537,
                                   headers={"Authorization": "Bearer session", "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)
        self.assertNotIn("inventory", [r.url.host for r in self.seen])

    def test_login_forwards_credentials_to_auth(self):
        response = self.client.post("/api/v1/auth/login", json={"username": "demo", "password": "password-demo"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "test-session")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.seen[-1].url.path, "/login")
        self.assertNotIn("inventory", [r.url.host for r in self.seen])

    def test_logout_forwards_token_without_requiring_active_session(self):
        self.active = False
        response = self.client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer expired-session"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.seen[-1].url.path, "/logout")
        self.assertNotIn("/introspect", [r.url.path for r in self.seen])
        self.assertIn(b"expired-session", self.seen[-1].content)

    def test_logout_requires_token(self):
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 401)
        self.assertEqual(self.seen, [])
