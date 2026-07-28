from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class VaultError(RuntimeError):
    """Raised when a personal vault cannot be opened safely."""


def generate_key() -> str:
    return Fernet.generate_key().decode("ascii")


def _normalize_key(key: str) -> bytes:
    value = key.strip().encode("ascii")
    try:
        Fernet(value)
    except Exception as exc:  # noqa: BLE001
        raise VaultError("STATE_ENCRYPTION_KEY no es una clave Fernet válida.") from exc
    return value


def encrypt_payload(payload: dict[str, Any], key: str) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Fernet(_normalize_key(key)).encrypt(raw)


def decrypt_payload(token: bytes, key: str) -> dict[str, Any]:
    try:
        raw = Fernet(_normalize_key(key)).decrypt(token)
    except InvalidToken as exc:
        raise VaultError("No se pudo descifrar el vault: clave incorrecta o archivo alterado.") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VaultError("El contenido descifrado no es JSON válido.") from exc
    if not isinstance(payload, dict):
        raise VaultError("El vault debe contener un objeto JSON.")
    return payload


def load_vault(path: Path, key: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.exists():
        return {}, {"configured": False, "reason": "vault_missing"}
    secret = (key or os.getenv("STATE_ENCRYPTION_KEY", "")).strip()
    if not secret:
        return {}, {"configured": False, "reason": "key_missing"}
    payload = decrypt_payload(path.read_bytes(), secret)
    return payload, {"configured": True, "reason": "ok"}


def encrypt_file(input_path: Path, output_path: Path, key: str) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VaultError("El archivo personal debe contener un objeto JSON.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(encrypt_payload(payload, key))


def decrypt_file(input_path: Path, output_path: Path, key: str) -> None:
    payload = decrypt_payload(input_path.read_bytes(), key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_key(args: argparse.Namespace) -> str:
    if args.key:
        return args.key
    if args.key_file:
        return Path(args.key_file).read_text(encoding="utf-8").strip()
    key = os.getenv("STATE_ENCRYPTION_KEY", "").strip()
    if not key:
        raise VaultError("Indica --key, --key-file o STATE_ENCRYPTION_KEY.")
    return key


def main() -> int:
    parser = argparse.ArgumentParser(description="Cifra o descifra el vault personal.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate-key", help="Genera una clave Fernet")
    gen.add_argument("--output")

    enc = sub.add_parser("encrypt", help="Cifra un JSON personal")
    enc.add_argument("--input", required=True)
    enc.add_argument("--output", required=True)
    enc.add_argument("--key")
    enc.add_argument("--key-file")

    dec = sub.add_parser("decrypt", help="Descifra un vault")
    dec.add_argument("--input", required=True)
    dec.add_argument("--output", required=True)
    dec.add_argument("--key")
    dec.add_argument("--key-file")

    args = parser.parse_args()
    if args.command == "generate-key":
        key = generate_key()
        if args.output:
            Path(args.output).write_text(key + "\n", encoding="utf-8")
        else:
            print(key)
        return 0

    key = _read_key(args)
    if args.command == "encrypt":
        encrypt_file(Path(args.input), Path(args.output), key)
    else:
        decrypt_file(Path(args.input), Path(args.output), key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
