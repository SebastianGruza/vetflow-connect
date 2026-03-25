from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

from src.core.crypto import generate_keypair, hash_plugin_files, sign, verify
from src.core.plugin_manifest import PluginStatus, serialize_manifest, verify_plugin


def test_sign_and_verify_roundtrip():
    private_key, public_key = generate_keypair()
    payload = b"plugin-manifest"
    signature = sign(payload, private_key)

    assert verify(payload, signature, public_key) is True
    assert verify(payload + b"-tampered", signature, public_key) is False


def test_verify_plugin_ok(tmp_path):
    private_key, public_key = generate_keypair()
    plugin_dir = tmp_path / "signed_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("PLUGIN = True\n", encoding="utf-8")

    manifest = {
        "name": "signed_plugin",
        "version": "1.0.0",
        "display_name": "Signed Plugin",
        "author": "VetFlow",
        "partner_id": "vetflow",
        "device_serial": "*",
        "license_type": "open",
        "expires_at": None,
        "signed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files_hash": hash_plugin_files(plugin_dir),
    }
    manifest_bytes = serialize_manifest(manifest)
    (plugin_dir / "manifest.json").write_bytes(manifest_bytes)
    (plugin_dir / "signature.sig").write_text(
        base64.b64encode(sign(manifest_bytes, private_key)).decode("ascii") + "\n",
        encoding="utf-8",
    )

    result = verify_plugin(plugin_dir, public_key, "prod")

    assert result.status == PluginStatus.OK
    assert result.manifest is not None
    assert result.manifest.display_name == "Signed Plugin"


def test_verify_plugin_expired(tmp_path):
    private_key, public_key = generate_keypair()
    plugin_dir = tmp_path / "expired_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("PLUGIN = True\n", encoding="utf-8")

    manifest = {
        "name": "expired_plugin",
        "version": "1.0.0",
        "display_name": "Expired Plugin",
        "author": "VetFlow",
        "partner_id": "vetflow",
        "device_serial": "*",
        "license_type": "partner",
        "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "signed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files_hash": hash_plugin_files(plugin_dir),
    }
    manifest_bytes = serialize_manifest(manifest)
    (plugin_dir / "manifest.json").write_bytes(manifest_bytes)
    (plugin_dir / "signature.sig").write_text(
        base64.b64encode(sign(manifest_bytes, private_key)).decode("ascii") + "\n",
        encoding="utf-8",
    )

    result = verify_plugin(plugin_dir, public_key, "prod")

    assert result.status == PluginStatus.EXPIRED


def test_verify_plugin_tampered(tmp_path):
    private_key, public_key = generate_keypair()
    plugin_dir = tmp_path / "tampered_plugin"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "plugin.py"
    plugin_file.write_text("PLUGIN = True\n", encoding="utf-8")

    manifest = {
        "name": "tampered_plugin",
        "version": "1.0.0",
        "display_name": "Tampered Plugin",
        "author": "VetFlow",
        "partner_id": "vetflow",
        "device_serial": "*",
        "license_type": "open",
        "expires_at": None,
        "signed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files_hash": hash_plugin_files(plugin_dir),
    }
    manifest_bytes = serialize_manifest(manifest)
    (plugin_dir / "manifest.json").write_bytes(manifest_bytes)
    (plugin_dir / "signature.sig").write_text(
        base64.b64encode(sign(manifest_bytes, private_key)).decode("ascii") + "\n",
        encoding="utf-8",
    )
    plugin_file.write_text("PLUGIN = False\n", encoding="utf-8")

    result = verify_plugin(plugin_dir, public_key, "prod")

    assert result.status == PluginStatus.TAMPERED


def test_verify_plugin_dev_mode_skips_missing_manifest(tmp_path):
    plugin_dir = tmp_path / "dev_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("PLUGIN = True\n", encoding="utf-8")

    result = verify_plugin(plugin_dir, b"unused", "dev")

    assert result.status == PluginStatus.DEV_MODE
