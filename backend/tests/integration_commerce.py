"""Prueba real por Gateway, Auth, Vault y MySQL. Crea datos ficticios identificables."""
import os
import ssl
import secrets
import time
import unittest
from datetime import datetime, timezone
import httpx

@unittest.skipUnless(os.getenv("DEMO_ADMIN_PASSWORD"), "Configura DEMO_ADMIN_PASSWORD para pruebas reales")
class CommerceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ca = os.getenv("API_CA_FILE")
        verify = ssl.create_default_context(cafile=ca) if ca else True
        cls.http = httpx.Client(base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000") + "/api/v1", timeout=30, verify=verify)
        password = os.environ["DEMO_ADMIN_PASSWORD"]
        cls.addClassCleanup(cls.http.close)
        for attempt in range(30):
            try:
                response = cls.http.post("/auth/login", json={"username": os.getenv("DEMO_ADMIN_USERNAME", "admin-demo"), "password": password})
                if response.status_code == 200:
                    cls.admin = {"Authorization": "Bearer " + response.json()["access_token"]}
                    return
            except httpx.RequestError:
                pass
            time.sleep(1)
        raise RuntimeError("Gateway/Auth no disponible")

    @classmethod
    def tearDownClass(cls):
        cls.http.close()

    def request(self, method, path, expected=200, headers=None, **kwargs):
        response = self.http.request(method, path, headers=headers, **kwargs)
        self.assertEqual(response.status_code, expected, f"{method} {path}: {response.text}")
        return response.json() if response.content else None

    def account(self):
        suffix = secrets.token_hex(5)
        password = secrets.token_urlsafe(18)
        row = self.request("POST", "/auth/register", 201, json={"username": "test-" + suffix, "password": password})
        token = self.request("POST", "/auth/login", json={"username": "test-" + suffix, "password": password})["access_token"]
        return row["id"], {"Authorization": "Bearer " + token}

    def test_complete_purchase_and_permissions(self):
        user_id, customer = self.account()
        _, stranger = self.account()
        profile = {"full_name": "Cliente de prueba", "email": f"test-{user_id}@example.invalid",
                   "phone": "900000000", "address": "Direccion ficticia 123"}
        self.request("POST", "/clients/me", 201, customer, json=profile)
        self.request("GET", f"/admin/clients/{user_id}", 403, customer)
        product = self.request("POST", "/admin/products", 201, self.admin, json={
            "name": "Prueba-commerce", "description": "Producto ficticio de prueba", "category": "cafe",
            "price": 3500, "stock": 5, "available": True, "featured": False})
        product_id = product["id"]
        body = {"items": [{"product_id": product_id, "quantity": 2}], "delivery_method": "delivery"}
        key = "order-" + secrets.token_hex(8)
        headers = {**customer, "Idempotency-Key": key}
        self.request("POST", "/orders", 409, headers, json=body)
        self.request("POST", "/clients/me/verification", 202, customer, json={})
        mail = self.request("GET", "/admin/mailbox", headers=self.admin)
        message = next(m for m in mail if m["user_id"] == user_id)
        token = message["message"].split(": ")[-1]
        self.request("POST", "/clients/verify-email", json={"token": token})
        self.request("POST", "/clients/verify-email", 400, json={"token": token})
        order = self.request("POST", "/orders", 201, headers, json=body)
        order_id = order["id"]
        self.assertEqual(order["total"], 7000)
        duplicate = self.request("POST", "/orders", 201, headers, json=body)
        self.assertEqual(duplicate["id"], order_id)
        self.request("POST", "/orders", 409, headers, json={**body, "delivery_method": "pickup"})
        self.request("GET", f"/orders/{order_id}", 404, stranger)
        self.request("PUT", f"/admin/orders/{order_id}/status", 409, self.admin, json={"status": "PREPARING"})
        pay_headers = {**customer, "Idempotency-Key": "pay-" + secrets.token_hex(8)}
        payment = self.request("POST", "/payments", 201, pay_headers, json={"order_id": order_id})
        self.assertEqual(payment["amount"], 7000)
        self.assertFalse(payment["real_charge"])
        self.request("POST", "/payments", 422, pay_headers, json={"order_id": order_id, "amount": 1})
        self.request("GET", f"/payments/{payment['id']}", 404, stranger)
        self.request("POST", f"/admin/payments/{payment['id']}/simulate", 403, customer, json={"result": "APPROVED"})
        self.request("POST", "/payments/webhook", 403, json={})
        rejected_id = payment["id"]
        self.request("POST", f"/admin/payments/{rejected_id}/simulate", headers=self.admin, json={"result": "REJECTED"})
        self.assertEqual(self.request("GET", f"/orders/{order_id}", headers=customer)["status"], "PENDING_PAYMENT")
        payment = self.request("POST", "/payments", 201,
            {**customer, "Idempotency-Key": "pay-retry-" + secrets.token_hex(8)}, json={"order_id": order_id})
        self.assertNotEqual(payment["id"], rejected_id)
        for _ in range(2):
            self.request("POST", f"/admin/payments/{payment['id']}/simulate", headers=self.admin, json={"result": "APPROVED"})
        self.assertEqual(self.request("GET", f"/orders/{order_id}", headers=customer)["status"], "PAID")
        # La caja virtual emite una sola venta y encola su boleta dummy.
        sale = self.request("POST", "/admin/sales", 201, self.admin, json={"order_id":order_id})
        self.assertEqual(sale["total"], 7000)
        again = self.request("POST", "/admin/sales", 201, self.admin, json={"order_id":order_id})
        self.assertEqual(sale["id"], again["id"])
        self.request("GET", f"/orders/{order_id}/receipt", 404, stranger)
        self.assertTrue(self.request("GET", f"/orders/{order_id}/receipt", headers=customer)["receipt_sent"])
        query = 'query($id:ID!){orderSummary(id:$id){id total customer{full_name} payment{status}}}'
        result = self.request("POST", "/graphql", headers=customer, json={"query":query,"variables":{"id":str(order_id)}})
        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["orderSummary"]["payment"]["status"], "APPROVED")
        denied = self.request("POST", "/graphql", headers=stranger, json={"query":query,"variables":{"id":str(order_id)}})
        self.assertIsNone(denied["data"]["orderSummary"])
        self.request("POST", "/graphql", 400, customer, json={"query":"{catalog(limit:10000){id}}"})
        self.request("GET", "/admin/users", 403, customer)
        self.request("GET", "/admin/users", headers=self.admin)
        today = datetime.now(timezone.utc).date().isoformat()
        report = self.request("GET", f"/admin/sales/report?start_date={today}&end_date={today}", headers=self.admin)
        self.assertIn("net_total", report)
        for status in ("PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"):
            self.request("PUT", f"/admin/orders/{order_id}/status", headers=self.admin, json={"status": status})
        # Una segunda compra impaga se puede cancelar y reponer sin duplicar stock.
        second_headers = {**customer, "Idempotency-Key": "cancel-" + secrets.token_hex(8)}
        second = self.request("POST", "/orders", 201, second_headers, json=body)
        for _ in range(2):
            self.request("POST", f"/orders/{second['id']}/cancel", headers=customer, json={"reason": "Cancelación de prueba"})
        self.request("POST", "/payments", 409, {**customer, "Idempotency-Key": "no-pay-" + secrets.token_hex(8)}, json={"order_id": second["id"]})
        products = self.request("GET", "/admin/products?limit=100", headers=self.admin)
        stored = next(p for p in products if p["id"] == product_id)
        self.assertEqual(stored["stock"], 3)
        # Pago aprobado: el cliente solicita y admin autoriza antes de preparar.
        third = self.request("POST", "/orders", 201, {**customer, "Idempotency-Key": "refund-" + secrets.token_hex(8)}, json=body)
        third_payment = self.request("POST", "/payments", 201, {**customer, "Idempotency-Key": "refund-pay-" + secrets.token_hex(8)}, json={"order_id": third["id"]})
        self.request("POST", f"/admin/payments/{third_payment['id']}/simulate", headers=self.admin, json={"result": "APPROVED"})
        asked = self.request("POST", f"/orders/{third['id']}/cancel", headers=customer, json={"reason": "Solicito cancelar compra"})
        self.assertEqual(asked["status"], "PAID")
        self.assertTrue(asked["cancellation_requested"])
        for _ in range(2):
            cancelled = self.request("POST", f"/orders/{third['id']}/cancel", headers=self.admin, json={"reason": "Cancelación autorizada"})
            self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(self.request("GET", f"/payments/{third_payment['id']}", headers=customer)["status"], "REFUNDED")
        products = self.request("GET", "/admin/products?limit=100", headers=self.admin)
        self.assertEqual(next(p for p in products if p["id"] == product_id)["stock"], 3)
        self.request("DELETE", f"/admin/products/{product_id}", 204, self.admin)
        self.request("DELETE", f"/admin/clients/{user_id}", 204, self.admin)


    def test_stock_concurrent(self):
        from concurrent.futures import ThreadPoolExecutor
        user_id, customer = self.account()
        profile = {"full_name": "Cliente de prueba", "email": f"test-{user_id}@example.invalid",
                   "phone": "900000000", "address": "Direccion ficticia 123"}
        self.request("POST", "/clients/me", 201, customer, json=profile)
        self.request("POST", "/clients/me/verification", 202, customer, json={})
        message = next(m for m in self.request("GET","/admin/mailbox",headers=self.admin) if m["user_id"] == user_id)
        self.request("POST", "/clients/verify-email", json={"token":message["message"].split(": ")[-1]})
        product = self.request("POST","/admin/products",201,self.admin,json={"name":"Stock concurrente","description":"Prueba ficticia",
            "category":"test","price":1000,"stock":1,"available":True,"featured":False})
        body = {"items":[{"product_id":product["id"],"quantity":1}],"delivery_method":"pickup"}
        def purchase(index):
            return self.http.post("/orders",headers={**customer,"Idempotency-Key":"concurrent-"+secrets.token_hex(8)},json=body).status_code
        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = list(pool.map(purchase,range(5)))
        self.assertEqual(statuses.count(201),1,statuses)
        self.assertEqual(statuses.count(409),4,statuses)
        for order in self.request("GET","/orders",headers=customer):
            self.request("POST",f"/orders/{order['id']}/cancel",headers=customer,json={"reason":"Limpieza de prueba concurrente"})
        products = self.request("GET","/admin/products?limit=100",headers=self.admin)
        self.assertEqual(next(p for p in products if p["id"] == product["id"])["stock"],1)
        self.request("DELETE",f"/admin/products/{product['id']}",204,self.admin)
        self.request("DELETE",f"/admin/clients/{user_id}",204,self.admin)


    def test_admin_assisted_registration(self):
        user_id, customer = self.account()
        profile = {"full_name": "Cliente de prueba", "email": f"test-{user_id}@example.invalid",
                   "phone": "900000000", "address": "Direccion ficticia 123"}
        self.request("POST",f"/admin/clients/{user_id}",201,self.admin,json=profile)
        self.request("POST",f"/admin/clients/{user_id}/verification",202,self.admin,json={})
        message = next(m for m in self.request("GET","/admin/mailbox",headers=self.admin) if m["user_id"] == user_id)
        self.request("POST","/clients/verify-email",json={"token":message["message"].split(": ")[-1]})
        self.assertTrue(self.request("GET","/clients/me",headers=customer)["email_verified"])
        self.request("DELETE",f"/admin/clients/{user_id}",204,self.admin)
        self.request("DELETE",f"/admin/users/{user_id}",204,self.admin)
        self.request("GET","/auth/me",401,customer)
