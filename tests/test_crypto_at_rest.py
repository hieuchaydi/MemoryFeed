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


if __name__ == "__main__":
    unittest.main()
