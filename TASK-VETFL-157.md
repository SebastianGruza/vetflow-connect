# TASK: VETFL-157 — VetFlowConnect Plugin Architecture Refactor

## Cel
Refaktor VetFlowConnect z monolitu na plugin architecture. Uproszczony setup: 
user wpisuje TYLKO API key + wybiera URL (dev/test/prod). Reszta konfiguracji (porty, IP urządzeń) 
zarządzana zdalnie z VetFlow web UI.

## Obecna struktura (do zmiany)
```
src/
├── agent.py          ← monolityczny agent (303 LOC)
├── hl7_listener.py   ← hardcoded HL7 listener
├── hl7_parser.py     ← hardcoded HL7 parser
├── config.py         ← config.json z devices, ports, IP
├── tray.py           ← system tray (OK, zachować)
├── vetflow_client.py ← API client (OK, rozszerzyć)
└── auto_discover.py  ← auto-discovery (OK, przenieść do core)
```

## Docelowa struktura
```
src/
├── core/
│   ├── __init__.py
│   ├── app.py              ← główna pętla, ładuje pluginy, zarządza lifecycle
│   ├── config.py            ← NOWY: API key + URL only, reszta z serwera
│   ├── plugin_base.py       ← DevicePlugin base class
│   ├── plugin_loader.py     ← dynamiczne ładowanie pluginów
│   ├── api_client.py        ← komunikacja z VetFlow API (rozszerzony vetflow_client.py)
│   ├── auto_discover.py     ← skanowanie sieci (przeniesiony)
│   └── tray.py              ← system tray (przeniesiony, rozszerzony o setup wizard)
│
├── plugins/
│   ├── __init__.py
│   └── skyla/
│       ├── __init__.py
│       ├── plugin.py         ← SkylaPlugin(DevicePlugin)
│       ├── hl7_listener.py   ← przeniesiony
│       ├── hl7_parser.py     ← przeniesiony
│       └── README.md         ← dokumentacja pluginu
│
├── setup_wizard.py           ← NOWY: okienko pierwszego uruchomienia
├── __init__.py
└── __main__.py
```

## Acceptance Criteria

### 1. Plugin Base Class (`core/plugin_base.py`)
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class VitalsData:
    device_serial: str
    timestamp: str
    measurements: dict  # {"spo2": 98, "hr": 72, "temp": 38.5, ...}

@dataclass  
class LabResult:
    device_serial: str
    timestamp: str
    panels: list[dict]  # CBC, Chemistry panels
    raw_message: str

class DevicePlugin(ABC):
    """Base class for all device plugins."""
    name: str           # "skyla-vm100"
    display_name: str   # "Skyla VM100 Blood Analyzer"
    protocol: str       # "hl7", "serial", "usb"
    device_type: str    # "lab_analyzer", "anesthesia_monitor", "fiscal_printer"
    version: str        # "1.0.0"
    
    @abstractmethod
    async def start(self, config: dict) -> None:
        """Start listening/connecting to device."""
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop and cleanup."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if device is reachable."""
    
    # Override one or both:
    async def on_vitals(self, data: VitalsData) -> None:
        """Called when vitals received (anesthesia monitors)."""
    
    async def on_lab_result(self, data: LabResult) -> None:
        """Called when lab result received (analyzers)."""
```

### 2. Simplified Config — Setup Wizard (`setup_wizard.py`)
Pierwsze uruchomienie (brak config.json) → okienko tkinter:

```
┌──────────────────────────────────────┐
│  🐾 VetFlowConnect — Konfiguracja   │
│                                       │
│  Klucz API: [________________________]│
│                                       │
│  Serwer:    ○ vet-flow.pl (produkcja) │
│             ○ test.vet-flow.pl (test)  │
│             ○ vetflow.gruzalab.pl (dev)│
│             ○ Inny: [________________]│
│                                       │
│  [  Połącz i zapisz  ]               │
│                                       │
│  Status: ⏳ Oczekiwanie...           │
└──────────────────────────────────────┘
```

Po kliknięciu "Połącz":
1. POST /api/device/register {api_key} → weryfikacja klucza
2. GET /api/device/config → pobranie konfiguracji urządzeń Z SERWERA
3. Zapisanie config.json (tylko api_key + url)
4. Przejście do normalnego trybu

### 3. Config z serwera (NOWE endpoint w VetFlow)
Konfiguracja urządzeń (porty, IP, typy) zarządzana na stronie VetFlow,
nie w config.json na komputerze kliniki.

Nowy endpoint w VetFlow:
```
GET /api/device/config
Authorization: Bearer <api_key>

Response:
{
    "clinic_id": 16,
    "clinic_name": "Klinika Górska",
    "devices": [
        {
            "name": "Skyla VM100",
            "plugin": "skyla",
            "protocol": "hl7",
            "host": "auto",        // auto-discover lub konkretne IP
            "port": 12221,
            "type": "lab_analyzer",
            "enabled": true
        }
    ],
    "settings": {
        "auto_discover": true,
        "heartbeat_interval": 60,
        "log_level": "INFO"
    }
}
```

UI w VetFlow: Ustawienia → Urządzenia → lista urządzeń z konfiguracją

### 4. Plugin Loader (`core/plugin_loader.py`)
- Skanuje `plugins/` directory
- Ładuje każdy plugin który ma `plugin.py` z klasą dziedziczącą DevicePlugin
- Matchuje plugin.name z device.plugin z config serwera
- Uruchamia plugin.start(device_config)

### 5. Skyla jako pierwszy plugin (`plugins/skyla/`)
- Przenieść hl7_listener.py + hl7_parser.py do plugins/skyla/
- Zaimplementować SkylaPlugin(DevicePlugin)
- on_lab_result → wysyła do VetFlow API (jak teraz)
- Musi działać identycznie jak przed refaktorem

### 6. Tray rozszerzony
- Po zalogowaniu: zielona ikona + "Połączono z Klinika Górska"
- Lista aktywnych pluginów w menu tray
- "Ustawienia" → otwiera VetFlow web w przeglądarce (ustawienia urządzeń)
- "Wyloguj" → usuwa config.json, wraca do setup wizard

### 7. Nowe endpoint w VetFlow (`src/vetflow/routers/device.py`)
```python
router = APIRouter(prefix="/api/device", tags=["device"])

@router.post("/register")     # weryfikacja API key, zwraca clinic info
@router.get("/config")         # konfiguracja urządzeń dla tego API key
@router.post("/heartbeat")     # "żyję" + status pluginów
@router.post("/lab-results")   # wyniki badań (istniejący, przenieść z lab_results.py)
@router.post("/vitals")        # vitale z monitora (NOWY, na przyszłość)
```

### 8. UI w VetFlow: Ustawienia → Urządzenia
Nowa zakładka w ustawieniach kliniki:
- Lista sparowanych urządzeń (z heartbeat status)
- Dodaj urządzenie: nazwa, plugin, host/port, typ
- Edytuj / Usuń
- Status: online/offline (ostatni heartbeat)

## Config.json — UPROSZCZONY
```json
{
    "api_key": "clinic_api_xxxx",
    "url": "https://vet-flow.pl",
    "log_file": "vetflow_connect.log"
}
```
To WSZYSTKO co user musi skonfigurować. Reszta pobierana z serwera.

## NIE ruszaj
- .github/ (CI/CD)
- tests/ (dodaj nowe, nie usuwaj starych)
- LICENSE, SECURITY.md, README.md (zaktualizuj README)
- icon.ico

## Jak wygenerować plugin (instrukcja dla producenta)
```
1. Skopiuj plugins/skyla/ jako template
2. Zmień plugin.py:
   - name = "twoj-device"
   - display_name = "Nazwa Urządzenia" 
   - protocol = "hl7" lub "serial"
   - Zaimplementuj start(), stop(), health_check()
   - W start(): nasłuchuj na porcie, parsuj dane
   - Wywołaj self.on_lab_result() lub self.on_vitals()
3. Przetestuj: python -m src --plugin twoj-device
4. Wyślij PR na GitHub lub skontaktuj się z VetFlow
```

## Commit format
feat(VETFL-157): refactor VetFlowConnect to plugin architecture
