"""Generate a fresh VetFlow signing keypair."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.crypto import generate_keypair


def main() -> None:
    private_pem, public_pem = generate_keypair()
    private_path = ROOT / "scripts" / "vetflow_private.pem"
    public_path = ROOT / "scripts" / "vetflow_public.pem"
    keys_path = ROOT / "src" / "core" / "keys.py"

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    keys_path.write_text(
        '"""Embedded VetFlow public signing key."""\n\n'
        f'VETFLOW_PUBLIC_KEY = """{public_pem.decode("utf-8")}"""\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
