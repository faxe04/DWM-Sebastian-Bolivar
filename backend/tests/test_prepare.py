"""La preparación debe poder repetirse sin reemplazar claves o configuración."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend.scripts import prepare

class PrepareTests(unittest.TestCase):
    def test_preserves_existing_secrets_and_env(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("", "auth", "gateway", "graphql", "services/inventory", "services/clients", "services/orders", "services/payments"):
                directory = root / name
                directory.mkdir(parents=True, exist_ok=True)
                (directory / ".env.example").write_text("DEMO=true", encoding="utf-8")
            with patch.object(prepare, "BACKEND", root), contextlib.redirect_stdout(io.StringIO()):
                prepare.prepare_secrets()
                prepare.prepare_env()
                prepare.prepare_certificate()
                original = (root / ".runtime" / "auth_db_password").read_text()
                certificate = (root / ".runtime" / "localhost.crt").read_bytes()
                (root / ".env").write_text("CUSTOM=true", encoding="utf-8")
                prepare.prepare_secrets()
                prepare.prepare_env()
                prepare.prepare_certificate()
                self.assertEqual((root / ".runtime" / "auth_db_password").read_text(), original)
                self.assertEqual((root / ".runtime" / "localhost.crt").read_bytes(), certificate)
                self.assertEqual((root / ".env").read_text(), "CUSTOM=true")
