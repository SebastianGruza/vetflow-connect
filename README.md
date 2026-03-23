# 🐾 VetFlowConnect

**Open-source HL7 agent for veterinary laboratory analyzers.**

VetFlowConnect is a lightweight Windows agent that listens for HL7 messages from veterinary blood analyzers (Skyla VM100, Tutti, and others) and automatically sends parsed results to [VetFlow](https://vet-flow.pl) — a cloud veterinary clinic management system.

## Why Open Source?

Veterinary clinics handle sensitive patient data. We believe the software running on clinic computers should be fully transparent and auditable. That's why VetFlowConnect is open source — you can inspect every line of code, build it yourself, and verify that the .exe does exactly what it claims.

## Features

- 🔍 **Auto-discovery** — scans local network for HL7 devices
- 🩸 **HL7 v2.x parser** — CBC (Complete Blood Count) and Chemistry panels
- 📡 **Real-time listening** — TCP server on configurable ports
- 🌐 **VetFlow API integration** — automatic upload of parsed results
- 🪟 **Windows .exe** — single-file executable, no installation needed
- 📋 **Logging** — full debug logs to file

## Supported Analyzers

| Analyzer | Protocol | Type | Status |
|----------|----------|------|--------|
| Skyla VM100 | HL7 v2.3.1 | CBC (morphology) | ✅ Tested |
| Skyla Tutti | HL7 v2.8 | Chemistry (biochemistry) | 🔄 In progress |

## Quick Start

### Download

Download the latest `VetFlowConnect.exe` from [GitHub Releases](https://github.com/SebastianGruza/vetflow-connect/releases).

### Configure

Create a `config.json` file in the same folder as the .exe:

```json
{
  "vetflow_url": "https://vet-flow.pl",
  "api_key": "your_clinic_api_key",
  "devices": [
    {"name": "VM100", "host": "auto", "port": 8888, "type": "cbc"},
    {"name": "Tutti", "host": "auto", "port": 8889, "type": "chemistry"}
  ],
  "auto_discover": true,
  "log_file": "vetflow_connect.log"
}
```

- `vetflow_url` — your VetFlow instance URL
- `api_key` — clinic API key (generate in VetFlow → Settings → Integrations)
- `devices` — list of analyzers (`host: "auto"` enables network discovery)
- `auto_discover` — scan local network for HL7 devices on startup

### Run

Double-click `VetFlowConnect.exe`. The agent will:

1. Scan the local network for HL7 devices
2. Start listening on configured ports
3. Parse incoming HL7 messages
4. Send results to VetFlow API

### Network Setup

```
┌──────────┐     HL7/TCP      ┌─────────────────┐    HTTPS     ┌──────────┐
│ Skyla    │ ───────────────→ │ VetFlowConnect  │ ──────────→ │ VetFlow  │
│ VM100    │    port 8888     │ (Windows PC)    │   API POST   │ (cloud)  │
└──────────┘                  └─────────────────┘              └──────────┘
```

Both the analyzer and the PC must be on the same local network (LAN).

## Build from Source

### Requirements

- Python 3.12+
- `aiohttp` (HTTP client)
- `pyinstaller` (for .exe build)

### Install dependencies

```bash
pip install aiohttp pyinstaller
```

### Run in development

```bash
cd src
python -m __main__
# or
python build_entry.py
```

### Build .exe

```bash
cd src
pyinstaller --onefile --name VetFlowConnect --icon ../icon.ico --add-data "../config.json.example;." --paths . build_entry.py
```

The .exe will be in `src/dist/VetFlowConnect.exe`.

### Verify the build

Every official release includes a SHA256 hash. To verify:

```powershell
# Windows PowerShell
Get-FileHash VetFlowConnect.exe -Algorithm SHA256
```

Compare the hash with the one published in the GitHub Release.

## Running Tests

```bash
cd tests
python -m pytest test_hl7_parser.py test_mllp.py test_xml_builder.py
```

## Contributing

Contributions welcome! Especially:

- 🔬 **New analyzer support** — add HL7 parsers for other vet analyzers
- 🐛 **Bug reports** — file issues with HL7 message samples (anonymized!)
- 📖 **Documentation** — setup guides for specific analyzers
- 🌍 **Translations** — UI messages in other languages

## Security

- VetFlowConnect only **listens** for HL7 on local network and **sends** to configured VetFlow URL
- No data is stored permanently (only log file)
- API key is stored in local `config.json` — protect this file
- All communication with VetFlow is over HTTPS
- The agent has **no remote access** capabilities — it cannot be controlled from outside

## License

MIT — see [LICENSE](LICENSE)

## About VetFlow

[VetFlow](https://vet-flow.pl) is a modern cloud veterinary clinic management system built in Poland. Features include appointment scheduling, medical records, inventory management, online booking, and laboratory integrations.

---

Made with 🐾 by the VetFlow team
