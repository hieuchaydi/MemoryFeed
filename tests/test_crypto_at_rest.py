from __future__ import annotations

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.crypto_at_rest import AtRestCrypto


class AtRestCryptoTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self) -> None:
        key = base64.urlsafe_b64encode(b"a" * 32).decode("ascii")
        with patch.dict(os.environ, {"MEMORY_ENCRYPTION_ENABLED": "1", "MEMORY_ENCRYPTION_KEY": key}, clear=False):
            crypto = AtRestCrypto()
            msg = b"hello-memoryfeed"
            enc = crypto.encrypt_bytes(msg)
            self.assertNotEqual(enc, msg)
            dec = crypto.decrypt_bytes(enc)
            self.assertEqual(dec, msg)

    def test_file_provider_generation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-enc-") as tmp:
            key_file = Path(tmp) / "master.key"
            with patch.dict(
                os.environ,
                {
                    "MEMORY_ENCRYPTION_ENABLED": "1",
                    "MEMORY_ENCRYPTION_KEY": "",
                    "MEMORY_ENCRYPTION_KEY_FILE": str(key_file),
                },
                clear=False,
            ):
                crypto = AtRestCrypto()
                self.assertTrue(crypto.state.enabled)
                self.assertIn(crypto.state.provider, {"generated_file", "file", "keyring", "env"})

    def test_media_folder_migration_writes_encrypted_files(self) -> None:
        key = base64.urlsafe_b64encode(b"b" * 32).decode("ascii")
        with tempfile.TemporaryDirectory(prefix="memoryfeed-media-enc-") as tmp:
            root = Path(tmp)
            plain = root / "images"
            enc = root / "images_enc"
            plain.mkdir(parents=True, exist_ok=True)
            (plain / "sample.jpg").write_bytes(b"raw-image-bytes")
            with patch.dict(
                os.environ,
                {
                    "MEMORY_ENCRYPTION_ENABLED": "1",
                    "MEMORY_ENCRYPTION_KEY": key,
                    "MEMORY_ENCRYPTION_ALGO": "chacha20poly1305",
                    "MEMORYFEED_DATA_DIR": str(root),
                },
                clear=False,
            ):
                crypto = AtRestCrypto()
                report = crypto.migrate_media_folder(plain, enc, limit=10)
                self.assertEqual(report["processed"], 1)
                self.assertEqual(report["encrypted"], 1)
                payload = (enc / "sample.jpg.menc").read_bytes()
                self.assertTrue(payload.startswith((b"MFENC1", b"MFENC2")))


if __name__ == "__main__":
    unittest.main()
