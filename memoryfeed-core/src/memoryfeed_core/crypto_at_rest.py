from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

DATA_DIR = Path(os.getenv("MEMORYFEED_DATA_DIR", str(Path.home() / ".memoryfeed"))).expanduser()


@dataclass(frozen=True)
class EncryptionState:
    enabled: bool
    provider: str


class AtRestCrypto:
    def __init__(self) -> None:
        self.mode = (os.getenv("MEMORY_ENCRYPTION_MODE", "").strip().lower() or "")
        if self.mode not in {"off", "compat", "strict"}:
            self.mode = "compat" if (os.getenv("MEMORY_ENCRYPTION_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}) else "off"
        self.enabled = self.mode != "off"
        self._key: bytes | None = None
        self._provider = "disabled"
        self._algo = "none"
        if self.enabled:
            self._key, self._provider = self._load_or_create_key()
            self._algo = _resolve_algo()

    @property
    def state(self) -> EncryptionState:
        return EncryptionState(enabled=self.enabled, provider=self._provider)

    def encrypt_bytes(self, plaintext: bytes, aad: bytes = b"memoryfeed") -> bytes:
        if not self.enabled:
            return plaintext
        key = self._require_key()
        if self._algo == "xchacha20poly1305":
            nonce = secrets.token_bytes(24)
            ciphertext = _xchacha_encrypt(key, nonce, plaintext, aad)
            return b"MFENC2" + nonce + ciphertext
        nonce = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(key)
        ciphertext = cipher.encrypt(nonce, plaintext, aad)
        return b"MFENC1" + nonce + ciphertext

    def decrypt_bytes(self, payload: bytes, aad: bytes = b"memoryfeed") -> bytes:
        if not self.enabled:
            return payload
        if not payload.startswith((b"MFENC1", b"MFENC2")):
            if self.mode == "strict":
                raise RuntimeError("plaintext payload blocked in strict encryption mode")
            return payload
        key = self._require_key()
        if payload.startswith(b"MFENC2"):
            nonce = payload[6:30]
            ciphertext = payload[30:]
            return _xchacha_decrypt(key, nonce, ciphertext, aad)
        nonce = payload[6:18]
        ciphertext = payload[18:]
        cipher = ChaCha20Poly1305(key)
        return cipher.decrypt(nonce, ciphertext, aad)

    def encrypt_file(self, src: Path, dst: Path, aad: bytes = b"memoryfeed:image") -> None:
        raw = src.read_bytes()
        enc = self.encrypt_bytes(raw, aad=aad)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(enc)

    def decrypt_file(self, src: Path, dst: Path, aad: bytes = b"memoryfeed:image") -> None:
        raw = src.read_bytes()
        dec = self.decrypt_bytes(raw, aad=aad)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(dec)

    def encrypt_text(self, value: str, aad: bytes = b"memoryfeed:text") -> str:
        raw = self.encrypt_bytes(value.encode("utf-8"), aad=aad)
        if raw.startswith(b"MFENC1"):
            return "enc:" + base64.urlsafe_b64encode(raw).decode("ascii")
        return value

    def decrypt_text(self, value: str, aad: bytes = b"memoryfeed:text") -> str:
        if not self.enabled:
            return value
        if not isinstance(value, str):
            return ""
        if not value.startswith("enc:"):
            if self.mode == "strict":
                raise RuntimeError("plaintext text blocked in strict encryption mode")
            return value
        blob = base64.urlsafe_b64decode(value[4:].encode("ascii"))
        plain = self.decrypt_bytes(blob, aad=aad)
        return plain.decode("utf-8", errors="replace")

    def _require_key(self) -> bytes:
        if not self._key:
            raise RuntimeError("at-rest encryption key not available")
        return self._key

    def _load_or_create_key(self) -> tuple[bytes, str]:
        env_key = os.getenv("MEMORY_ENCRYPTION_KEY", "").strip()
        if env_key:
            return _decode_key(env_key), "env"

        keyring_key = _try_keyring_get()
        if keyring_key:
            return keyring_key, "keyring"

        key_file = Path(os.getenv("MEMORY_ENCRYPTION_KEY_FILE", str(DATA_DIR / "keys" / "master.key"))).expanduser()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if key_file.exists() and key_file.stat().st_size > 0:
            return _decode_key(key_file.read_text(encoding="utf-8").strip()), "file"

        generated = secrets.token_bytes(32)
        key_file.write_text(base64.urlsafe_b64encode(generated).decode("ascii"), encoding="utf-8")
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        _try_keyring_set(generated)
        return generated, "generated_file"

    def migration_manifest_path(self) -> Path:
        return DATA_DIR / "migrations" / "encryption_manifest.json"

    def migrate_media_folder(self, plain_dir: Path, encrypted_dir: Path, limit: int = 5000) -> dict[str, int]:
        if not self.enabled:
            return {"processed": 0, "encrypted": 0, "skipped": 0}
        plain_dir.mkdir(parents=True, exist_ok=True)
        encrypted_dir.mkdir(parents=True, exist_ok=True)
        files = [p for p in plain_dir.glob("*") if p.is_file()][: int(limit)]
        encrypted = 0
        skipped = 0
        for src in files:
            dst = encrypted_dir / f"{src.name}.menc"
            if dst.exists() and dst.stat().st_size > 0:
                skipped += 1
                continue
            self.encrypt_file(src, dst, aad=b"memoryfeed:image")
            encrypted += 1
        manifest = self.migration_manifest_path()
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(
                {
                    "algo": self._algo,
                    "provider": self._provider,
                    "processed": len(files),
                    "encrypted": encrypted,
                    "skipped": skipped,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {"processed": len(files), "encrypted": encrypted, "skipped": skipped}


def _decode_key(raw: str) -> bytes:
    blob = base64.urlsafe_b64decode(raw.encode("ascii"))
    if len(blob) != 32:
        raise ValueError("MEMORY_ENCRYPTION_KEY must decode to 32 bytes")
    return blob


def _try_keyring_get() -> bytes | None:
    try:
        import keyring  # type: ignore

        raw = keyring.get_password("memoryfeed", "master_key")
        if not raw:
            return None
        return _decode_key(raw)
    except Exception:
        return None


def _try_keyring_set(key: bytes) -> None:
    try:
        import keyring  # type: ignore

        raw = base64.urlsafe_b64encode(key).decode("ascii")
        keyring.set_password("memoryfeed", "master_key", raw)
    except Exception:
        return


def _resolve_algo() -> str:
    requested = (os.getenv("MEMORY_ENCRYPTION_ALGO", "xchacha20poly1305").strip().lower() or "xchacha20poly1305")
    if requested == "xchacha20poly1305":
        try:
            import nacl.bindings  # type: ignore

            _ = nacl.bindings.crypto_aead_xchacha20poly1305_ietf_encrypt
            return requested
        except Exception:
            return "chacha20poly1305"
    return "chacha20poly1305"


def _xchacha_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    import nacl.bindings  # type: ignore

    return nacl.bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(plaintext, aad, nonce, key)


def _xchacha_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    import nacl.bindings  # type: ignore

    return nacl.bindings.crypto_aead_xchacha20poly1305_ietf_decrypt(ciphertext, aad, nonce, key)
