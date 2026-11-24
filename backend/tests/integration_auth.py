import os
import time
import unittest
import httpx


@unittest.skipUnless(os.getenv("AUTH_INTROSPECTION_SECRET") and os.getenv("DEMO_ADMIN_PASSWORD"),
                     "Configura AUTH_INTROSPECTION_SECRET y DEMO_ADMIN_PASSWORD")
class AuthIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = httpx.Client(base_url=os.getenv("AUTH_TEST_URL", "http://localhost:8100"), timeout=10,
            headers={"X-Gateway-Auth-Secret": os.environ["AUTH_INTROSPECTION_SECRET"]})
        cls.password = os.environ["DEMO_ADMIN_PASSWORD"]
        cls.addClassCleanup(cls.client.close)
        for attempt in range(30):
            try:
                if cls.client.get("/health").status_code == 200:
                    return
            except httpx.RequestError:
                pass
            time.sleep(1)
        raise RuntimeError("Auth no alcanzó estado listo")

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_login_introspection_logout(self):
        response = self.client.post("/login", json={"username": os.getenv("DEMO_ADMIN_USERNAME", "admin-demo"), "password": self.password})
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        try:
            identity = self.client.post("/introspect", json={"token": token}).json()
            self.assertTrue(identity["active"])
            self.assertEqual(identity["roles"], ["admin"])
            self.assertNotIn("password_hash", identity)
        finally:
            self.assertEqual(self.client.post("/logout", json={"token": token}).status_code, 200)
        self.assertEqual(self.client.post("/introspect", json={"token": token}).json(), {"active": False})
        self.assertEqual(self.client.post("/logout", json={"token": token}).status_code, 200)

    @unittest.skipUnless(os.getenv("DEMO_CLIENT_PASSWORD"), "Configura DEMO_CLIENT_PASSWORD")
    def test_customer_role(self):
        password = os.environ["DEMO_CLIENT_PASSWORD"]
        response = self.client.post("/login", json={"username": os.getenv("DEMO_CLIENT_USERNAME", "cliente-demo"), "password": password})
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        try:
            self.assertEqual(self.client.post("/introspect", json={"token": token}).json()["roles"], ["client"])
        finally:
            self.client.post("/logout", json={"token": token})

    def test_wrong_credentials(self):
        self.assertEqual(self.client.post("/login", json={"username": os.getenv("DEMO_ADMIN_USERNAME", "admin-demo"), "password": "incorrecta"}).status_code, 401)

    def test_unauthorized_component(self):
        response = self.client.post("/introspect", json={"token": "test"}, headers={"X-Gateway-Auth-Secret": "incorrecto"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
