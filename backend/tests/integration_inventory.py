"""Pruebas contra el inventario real y MySQL, dentro de la red privada."""
import os
import time
import unittest
import uuid
import httpx


@unittest.skipUnless(os.getenv("INVENTORY_TEST_SECRET"), "Configura INVENTORY_TEST_SECRET")
class InventoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        secret = os.environ["INVENTORY_TEST_SECRET"]
        cls.client = httpx.Client(base_url=os.getenv("INVENTORY_TEST_URL", "http://localhost:9000"), timeout=5,
                                 headers={"X-Gateway-Secret": secret})
        cls.addClassCleanup(cls.client.close)
        for attempt in range(30):
            try:
                if cls.client.get("/health").status_code == 200:
                    break
            except httpx.RequestError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Inventario no alcanzó estado listo")
        cls.admin = {"X-Authenticated-User": "1", "X-Authenticated-Roles": "admin"}
        cls.product = {"name": "Prueba " + uuid.uuid4().hex[:8], "description": "Dato de prueba",
                       "category": "test", "price": 2500, "stock": 2, "available": True, "featured": False}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_direct_access_denied(self):
        response = self.client.get("/products", headers={"X-Gateway-Secret": "incorrect"})
        self.assertEqual(response.status_code, 403)

    def test_customer_cannot_write(self):
        response = self.client.post("/admin/products", json=self.product,
                                   headers={"X-Authenticated-User": "2", "X-Authenticated-Roles": "client"})
        self.assertEqual(response.status_code, 403)

    def test_database_lifecycle(self):
        created = self.client.post("/admin/products", json=self.product, headers=self.admin)
        self.assertEqual(created.status_code, 201, created.text)
        product_id = created.json()["id"]
        try:
            public = self.client.get(f"/products/{product_id}")
            self.assertEqual(public.status_code, 200)
            self.assertEqual(public.json()["price"], 2500)
            self.assertNotIn("stock", public.json())
            self.assertNotIn("identity", public.json())
            replacement = {**self.product, "stock": 0}
            updated = self.client.put(f"/admin/products/{product_id}", json=replacement, headers=self.admin)
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertTrue(updated.json()["available"])  # El interruptor administrativo se conserva.
            self.assertFalse(self.client.get(f"/products/{product_id}").json()["available"])
            repeated = self.client.put(f"/admin/products/{product_id}", json=replacement, headers=self.admin)
            self.assertEqual(repeated.status_code, 200)
            filtered = self.client.get("/products", params={"available": "true", "category": "test"})
            self.assertNotIn(product_id, [p["id"] for p in filtered.json()])
            # El texto se parametriza: no puede alterar la consulta SQL.
            injection = self.client.get("/products", params={"category": "' OR 1=1 --"})
            self.assertEqual(injection.json(), [])
        finally:
            deleted = self.client.delete(f"/admin/products/{product_id}", headers=self.admin)
            self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/products/{product_id}").status_code, 404)

    def test_invalid_price_and_extra_fields(self):
        for changes in ({"price": -1}, {"price": 2.5}, {"price": True}, {"stock": -1}, {"role": "admin"}):
            response = self.client.post("/admin/products", json={**self.product, **changes}, headers=self.admin)
            self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
