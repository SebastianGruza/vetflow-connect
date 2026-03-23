# Security Policy

## What VetFlowConnect Does

VetFlowConnect is a local HL7 agent that:
1. **Listens** for HL7 messages on local network TCP ports
2. **Parses** blood analyzer results (CBC, chemistry)
3. **Sends** parsed data to a configured VetFlow server via HTTPS

## What VetFlowConnect Does NOT Do

- ❌ Does not accept incoming connections from the internet
- ❌ Does not store patient data permanently (only transient logs)
- ❌ Does not have remote control or shell capabilities
- ❌ Does not access any files outside its own directory
- ❌ Does not phone home, collect telemetry, or send data anywhere except the configured `vetflow_url`

## Reporting Vulnerabilities

If you find a security vulnerability, please report it responsibly:

1. **Email:** security@vet-flow.pl
2. **Do NOT** open a public GitHub issue for security vulnerabilities

We will respond within 48 hours and work with you to resolve the issue.

## Verifying Builds

Every release includes a SHA256 hash file. To verify your download:

```powershell
# Windows PowerShell
Get-FileHash VetFlowConnect.exe -Algorithm SHA256
```

Compare the output with the `.sha256` file from the same release.

## Building from Source

For maximum trust, build from source:

```bash
git clone https://github.com/SebastianGruza/vetflow-connect.git
cd vetflow-connect/src
pip install pyinstaller aiohttp
pyinstaller --onefile --name VetFlowConnect --paths . build_entry.py
```
