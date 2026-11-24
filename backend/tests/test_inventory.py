import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from mysql.connector import OperationalError
with patch("dotenv.load_dotenv", return_value=False):
    from backend.services.inventory import main, config


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        env = patch.object(config, "INTERNAL_GATEWAY_SECRET", "test-secret")
        env.start()
        self.addCleanup(env.stop)
        mock_db = patch.object(main, "db", self.repository)
        mock_db.start()
        self.addCleanup(mock_db.stop)
        self.product = {"id": 1, "name": "Latte", "description": "Café con leche", "category": "cafe", "price": 2500, "stock": 3, "available": True, "featured": False}
        self.repository.get_product.return_value = self.product
        self.repository.list_products.return_value = [self.product]
        self.repository.create_product.return_value = self.product
        self.client = TestClient(main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.internal = {"X-Gateway-Secret": "test-secret"}
        self.admin = {**self.internal, "X-Authenticated-User": "1", "X-Authenticated-Roles": "admin"}
        self.input = {k: v for k, v in self.product.items() if k != "id"}


    def test_private_service_rejects_direct_request(self):
        self.assertEqual(self.client.get("/products").status_code, 403)
        self.repository.list_products.assert_not_called()


    def test_forged_role_without_service_secret_is_denied(self):
        response = self.client.post("/admin/products", json=self.input, headers={"X-Authenticated-User": "fake", "X-Authenticated-Roles": "admin"})
        self.assertEqual(response.status_code, 403)
        self.repository.create_product.assert_not_called()


    def test_public_response_minimizes_fields(self):
        response = self.client.get("/products", headers=self.internal)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("stock", response.json()[0])
        self.assertNotIn("identity", response.json()[0])


    def test_zero_stock_means_unavailable(self):
        self.repository.get_product.return_value = {**self.product, "stock": 0}
        self.assertFalse(self.client.get("/products/1", headers=self.internal).json()["available"])


    def test_customer_cannot_write(self):
        response = self.client.post("/admin/products", json=self.input, headers={**self.internal, "X-Authenticated-User": "2", "X-Authenticated-Roles": "client"})
        self.assertEqual(response.status_code, 403)
        self.repository.create_product.assert_not_called()


    def test_create_and_reject_invalid_inputs(self):
        self.assertEqual(self.client.post("/admin/products", json=self.input, headers=self.admin).status_code, 201)
        for changes in ({"price": -1}, {"price": 1.5}, {"price": True}, {"stock": -1}, {"name": "  "}, {"role": "admin"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.post("/admin/products", json={**self.input, **changes}, headers=self.admin).status_code, 422)


    def test_delete_is_logical_and_has_no_body(self):
        self.repository.delete_product.return_value = True
        response = self.client.delete("/admin/products/1", headers=self.admin)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.repository.delete_product.assert_called_once_with(1)


    def test_unknown_product(self):
        self.repository.get_product.return_value = None
        self.assertEqual(self.client.get("/products/99", headers=self.internal).status_code, 404)


    def test_database_failure_does_not_leak_details(self):
        self.repository.list_products.side_effect = OperationalError("password=hidden")
        response = self.client.get("/products", headers=self.internal)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("hidden", response.text)


    def test_pagination_limits(self):
        self.assertEqual(self.client.get("/products?limit=101", headers=self.internal).status_code, 422)
        self.assertEqual(self.client.get("/products?skip=-1", headers=self.internal).status_code, 422)
