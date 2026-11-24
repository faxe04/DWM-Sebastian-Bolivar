import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
with patch("dotenv.load_dotenv", return_value=False):
    from backend.auth import main
    from backend.auth.security import hash_password, verify_password, token_hash


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password_hash = hash_password("test-password")

    def setUp(self):
        self.db = Mock()
        self.user = {"id": 7, "username": "cliente", "password_hash": self.password_hash, "role": "client", "enabled": True}
        self.db.get_user.return_value = self.user
        self.db.get_session.return_value = None
        for replacement in [patch.object(main, "db", self.db), patch.object(main.config, "AUTH_INTROSPECTION_SECRET", "test-auth")]:
            replacement.start()
            self.addCleanup(replacement.stop)
        self.client = TestClient(main.app)
        self.headers = {"X-Gateway-Auth-Secret": "test-auth"}

    def test_private_login(self):
        result = self.client.post("/login", json={"username": "cliente", "password": "test-password"})
        self.assertEqual(result.status_code, 403)
        self.db.get_user.assert_not_called()

    def test_login_stores_only_token_hash(self):
        result = self.client.post("/login", headers=self.headers, json={"username": "cliente", "password": "test-password"})
        self.assertEqual(result.status_code, 200)
        token = result.json()["access_token"]
        self.assertEqual(self.db.create_session.call_args.args[0], token_hash(token))
        self.assertNotEqual(self.db.create_session.call_args.args[0], token)
        self.assertEqual(result.headers["cache-control"], "no-store")

    def test_wrong_password_missing_or_disabled_user(self):
        for user in [self.user, None, {**self.user, "enabled": False}]:
            self.db.get_user.return_value = user
            response = self.client.post("/login", headers=self.headers, json={"username": "cliente", "password": "incorrect"})
            self.assertEqual(response.status_code, 401)
        self.db.create_session.assert_not_called()

    def test_introspection_and_inactive_session(self):
        response = self.client.post("/introspect", headers=self.headers, json={"token": "unknown"})
        self.assertEqual(response.json(), {"active": False})
        self.db.get_session.return_value = {"user_id": 7, "username": "cliente", "role": "client", "expires_at": datetime.utcnow() + timedelta(minutes=15)}
        response = self.client.post("/introspect", headers=self.headers, json={"token": "valid"})
        self.assertEqual(response.json()["roles"], ["client"])
        self.assertEqual(response.json()["user_id"], "7")
        self.assertNotIn("password_hash", response.json())

    def test_logout_removes_hash(self):
        response = self.client.post("/logout", headers=self.headers, json={"token": "valid"})
        self.assertEqual(response.status_code, 200)
        self.db.delete_session.assert_called_once_with(token_hash("valid"))

    def test_password_hashes_are_salted(self):
        second = hash_password("test-password")
        self.assertNotEqual(second, self.password_hash)
        self.assertTrue(verify_password("test-password", second))
        self.assertFalse(verify_password("wrong", second))
