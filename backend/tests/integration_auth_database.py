"""Ejecutar dentro del contenedor Auth, con su propia credencial MySQL."""
import os
from unittest.mock import patch
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from mysql.connector import Error
with patch("dotenv.load_dotenv", return_value=False):
    from backend.auth import db
    from backend.auth.security import token_hash


@unittest.skipUnless(os.getenv("RUN_AUTH_DATABASE_TESTS") == "true",
                     "Requiere RUN_AUTH_DATABASE_TESTS=true y DB_* de Auth en el entorno")
class AuthDatabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.user = db.get_user(os.getenv("DEMO_ADMIN_USERNAME", "admin-demo"))
        self.token = secrets.token_urlsafe(32)
        self.fingerprint = token_hash(self.token)
        self.addCleanup(db.delete_session, self.fingerprint)

    def test_expired_session_is_inactive(self):
        expired = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        db.create_session(self.fingerprint, self.user["id"], expired)
        self.assertIsNone(db.get_session(self.fingerprint))

    def test_session_is_stored_and_revoked(self):
        expiration = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)
        db.create_session(self.fingerprint, self.user["id"], expiration)
        self.assertEqual(db.get_session(self.fingerprint)["user_id"], self.user["id"])
        with db.connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT token_hash FROM sessions WHERE token_hash=%s", (self.fingerprint,))
            self.assertNotEqual(cursor.fetchone()[0], self.token)
        db.delete_session(self.fingerprint)
        self.assertIsNone(db.get_session(self.fingerprint))

    def test_auth_cannot_read_inventory_database(self):
        with self.assertRaises(Error):
            with db.connection() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT id FROM inventory.products LIMIT 1")
                cursor.fetchall()
