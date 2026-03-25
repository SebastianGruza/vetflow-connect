"""Sign a plugin directory by generating manifest.json and signature.sig."""

from __future__ import annotations

import argparse
import base64
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.crypto import hash_plugin_files, sign
from core.plugin_manifest import serialize_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Sign a VetFlow plugin directory.")
    parser.add_argument("--plugin", required=True, type=Path, help="Path to the plugin directory")
    parser.add_argument("--key", required=True, type=Path, help="Path to the RSA private key PEM")
    parser.add_argument("--name", help="Plugin name override")
    parser.add_argument("--display-name", help="Plugin display name override")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--author", default="VetFlow")
    parser.add_argument("--partner-id", default="vetflow")
    parser.add_argument("--device-serial", default="*")
    parser.add_argument("--license-type", choices=("open", "partner", "device"))
    parser.add_argument("--expires", help="Expiry date in YYYY-MM-DD")
    args = parser.parse_args()

    plugin_dir = args.plugin.resolve()
    private_key = args.key.read_bytes()
    expires_at = None
    if args.expires:
        expires_at = datetime.strptime(args.expires, "%Y-%m-%d").replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")

    license_type = args.license_type or ("open" if expires_at is None else "partner")
    manifest_payload = {
        "name": args.name or plugin_dir.name,
        "version": args.version,
        "display_name": args.display_name or plugin_dir.name.replace("_", " ").title(),
        "author": args.author,
        "partner_id": args.partner_id,
        "device_serial": args.device_serial,
        "license_type": license_type,
        "expires_at": expires_at,
        "signed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files_hash": hash_plugin_files(plugin_dir),
    }
    manifest_bytes = serialize_manifest(manifest_payload)
    signature = sign(manifest_bytes, private_key)

    (plugin_dir / "manifest.json").write_bytes(manifest_bytes)
    (plugin_dir / "signature.sig").write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
