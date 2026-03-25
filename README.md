# VetFlowConnect

Open-source desktop connector for VetFlow device integrations.

VetFlowConnect now uses a plugin architecture. The local app stores only an API key and the VetFlow URL; device definitions, ports, hosts, and feature flags come from VetFlow over `/api/device/config`.

## Architecture

```text
src/
├── core/
│   ├── app.py
│   ├── api_client.py
│   ├── auto_discover.py
│   ├── config.py
│   ├── plugin_base.py
│   ├── plugin_loader.py
│   └── tray.py
├── plugins/
│   └── skyla/
│       ├── plugin.py
│       ├── hl7_listener.py
│       ├── hl7_parser.py
│       └── README.md
└── setup_wizard.py
```

Key points:

- `core/plugin_base.py` defines the `DevicePlugin` contract and shared payload dataclasses.
- `core/plugin_loader.py` scans `plugins/` and loads plugin classes dynamically.
- `core/app.py` validates the API key, fetches remote config, starts plugins, and sends heartbeats.
- `setup_wizard.py` handles first-run configuration with a simple Tkinter form.
- `plugins/skyla/` is the first migrated plugin and preserves the current HL7 parsing/listener behavior.

## First Run

If `config.json` is missing, VetFlowConnect opens a setup wizard with:

- API key input
- Server choice:
  - `vet-flow.pl`
  - `test.vet-flow.pl`
  - `vetflow.gruzalab.pl`
  - custom URL
- `Connect & Save` button
- status label

The wizard:

1. Calls `POST /api/device/register`
2. Calls `GET /api/device/config`
3. Saves the local config only after both requests succeed

Local config is intentionally minimal:

```json
{
  "api_key": "clinic_api_key_here",
  "url": "https://vet-flow.pl",
  "log_file": "vetflow_connect.log"
}
```

## Runtime Flow

1. VetFlowConnect loads local config or launches the setup wizard.
2. It verifies the API key with VetFlow.
3. It downloads the clinic device configuration.
4. It loads enabled plugins from `plugins/`.
5. Each plugin starts with its server-provided device config.
6. The tray icon shows connection state and active plugin health.
7. The app sends heartbeats to VetFlow.

## Tray

The tray app now includes:

- connected clinic status
- active plugin status lines
- `Ustawienia` shortcut to VetFlow device settings in the browser
- `Wyloguj` to remove `config.json` and return to the setup wizard
- `Pokaż logi`
- `Zamknij`

## Supported Plugins

| Plugin | Protocol | Type | Status |
| --- | --- | --- | --- |
| `skyla` | HL7 / MLLP | lab_analyzer | bundled |

## Creating a New Plugin

Use `plugins/skyla/` as the template.

1. Copy `plugins/skyla/` to a new directory.
2. Update `plugin.py`:
   - set `name`
   - set `display_name`
   - set `protocol`
   - set `device_type`
   - implement `start()`, `stop()`, `health_check()`
3. Emit data with `self.on_lab_result(...)` or `self.on_vitals(...)`.
4. Test with `python -m src --plugin your-plugin-name`.

## Development

Requirements:

- Python 3.12+
- `aiohttp`
- `pystray`
- `Pillow`

Run locally:

```bash
python -m src
```

Build the Windows executable:

```bash
cd src
pyinstaller --onefile --name VetFlowConnect --icon ../icon.ico --add-data "../config.json.example;." --paths . build_entry.py
```

Run tests:

```bash
python -m pytest tests
```

## Security

- Local configuration stores only the API key, VetFlow URL, and log file path.
- Device topology is managed centrally in VetFlow.
- VetFlowConnect listens locally and sends data outbound to VetFlow only.
- HTTPS should be used for every production VetFlow URL.

## License

MIT. See `LICENSE`.
