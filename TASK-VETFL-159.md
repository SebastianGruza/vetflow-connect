# TASK: VETFL-159 — Plugin Signature Verification

## Cel
VetFlowConnect weryfikuje podpisy pluginów. Dev mode = bez sprawdzania. 
Prod mode = plugin musi być podpisany kluczem VetFlow żeby działał.

## Kontekst biznesowy
- Skyla VM100 plugin jest open source (reference) ALE może być licencjonowany per urządzenie
- Producent (np. Skyla wypożycza Przemkowi analizator) → Przemek dostaje roczną licencję na plugin
- Bez ważnej licencji plugin wyświetla: "Licencja wygasła — skontaktuj się z dostawcą"
- Dev mode (localhost / vetflow.gruzalab.pl) = pluginy działają bez podpisu

## Architektura

### Klucze
```
VetFlow Private Key (RSA 2048) → trzymany TYLKO na serwerze (Partner Portal)
VetFlow Public Key → wbudowany w VetFlowConnect exe
```

### Podpisany plugin = plik .vfplugin
```
moj-plugin.vfplugin (ZIP):
├── manifest.json       ← metadata: name, version, author, expires_at
├── signature.sig       ← RSA podpis manifest.json + hash plików
├── plugin.py           ← kod pluginu
├── hl7_listener.py     ← dodatkowe pliki
└── README.md
```

### manifest.json
```json
{
    "name": "skyla",
    "version": "1.0.0",
    "display_name": "Skyla VM100 Blood Analyzer",
    "author": "VetFlow",
    "partner_id": "vetflow",
    "device_serial": "*",
    "license_type": "open",
    "expires_at": null,
    "signed_at": "2026-03-25T20:00:00Z",
    "files_hash": "sha256:abc123..."
}
```

### license_type
- `"open"` — darmowy, bez expiry (np. Skyla reference plugin)
- `"partner"` — licencjonowany per partner, expires_at = data
- `"device"` — licencjonowany per serial number urządzenia

### Weryfikacja flow
```python
def verify_plugin(plugin_dir: Path, mode: str) -> PluginStatus:
    # 1. Dev mode? → skip verification
    if mode == "dev":
        return PluginStatus.OK
    
    # 2. Read manifest.json
    manifest = load_manifest(plugin_dir / "manifest.json")
    
    # 3. Check signature
    signature = load_signature(plugin_dir / "signature.sig")
    if not rsa_verify(manifest_bytes, signature, VETFLOW_PUBLIC_KEY):
        return PluginStatus.INVALID_SIGNATURE
    
    # 4. Check expiry
    if manifest.expires_at and now() > manifest.expires_at:
        return PluginStatus.EXPIRED
    
    # 5. Check files hash (no tampering)
    actual_hash = hash_plugin_files(plugin_dir)
    if actual_hash != manifest.files_hash:
        return PluginStatus.TAMPERED
    
    return PluginStatus.OK
```

## Acceptance Criteria

### 1. Klucze RSA (`core/crypto.py`) — NOWY plik
- Generowanie pary kluczy: `generate_keypair() → (private_pem, public_pem)`
- Podpisywanie: `sign(data: bytes, private_key: bytes) → signature: bytes`  
- Weryfikacja: `verify(data: bytes, signature: bytes, public_key: bytes) → bool`
- Hashowanie plików pluginu: `hash_plugin_files(plugin_dir: Path) → str`
- Użyć `cryptography` library (RSA 2048, PKCS1v15, SHA256)

### 2. Manifest + Signature model (`core/plugin_manifest.py`) — NOWY plik
- `PluginManifest` dataclass (name, version, author, partner_id, device_serial, license_type, expires_at, signed_at, files_hash)
- `PluginStatus` enum: OK, NO_MANIFEST, INVALID_SIGNATURE, EXPIRED, TAMPERED, DEV_MODE
- `load_manifest(path) → PluginManifest`
- `verify_plugin(plugin_dir, public_key, mode) → PluginStatus`

### 3. Public key wbudowany (`core/keys.py`)
- VETFLOW_PUBLIC_KEY jako const string (PEM)
- Na start: wygeneruj parę → public key tu, private key w osobnym pliku (NIE w repo!)

### 4. Plugin Loader update (`core/plugin_loader.py`)
- Przed załadowaniem pluginu → `verify_plugin()`
- Dev mode (url zawiera "localhost" lub "gruzalab") → skip verification
- Prod mode → require valid signature
- Expired → plugin się ładuje ale tray pokazuje ⚠️ "Licencja pluginu X wygasła"
- Invalid/Tampered → plugin NIE ładuje się, tray pokazuje ❌

### 5. Tray status update
- OK → 🟢 "Plugin Skyla: aktywny (licencja: bezterminowa)"
- Expired → 🟡 "Plugin Skyla: licencja wygasła DD.MM.YYYY"
- Invalid → 🔴 "Plugin Skyla: nieprawidłowy podpis"

### 6. CLI do podpisywania (`scripts/sign_plugin.py`)
- `python scripts/sign_plugin.py --plugin plugins/skyla/ --key private_key.pem --expires 2027-03-25`
- Generuje manifest.json + signature.sig w katalogu pluginu
- Ten skrypt NIE idzie do publicznego repo — tylko na naszym serwerze

### 7. CLI do generowania kluczy (`scripts/generate_keys.py`)
- `python scripts/generate_keys.py`
- Tworzy `vetflow_private.pem` + `vetflow_public.pem`
- Private key → NIGDY w repo. Public key → `core/keys.py`

## Dev mode detection
```python
def is_dev_mode(url: str) -> bool:
    return any(x in url for x in ["localhost", "127.0.0.1", "gruzalab.pl", "test.vet-flow.pl"])
```

## NIE ruszaj
- plugins/skyla/ (nie dodawaj jeszcze podpisu — to zrobimy osobno)
- tests/ (dodaj nowe testy dla crypto + verification)
- .github/

## Commit format
feat(VETFL-159): plugin signature verification — RSA signing + dev mode bypass
