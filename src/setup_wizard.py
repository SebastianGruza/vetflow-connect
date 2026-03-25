"""First-run setup wizard for VetFlowConnect."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass

try:
    from .core.api_client import VetFlowClient
    from .core.config import Config, SERVER_CHOICES, normalize_url, save_config
except ImportError:
    from core.api_client import VetFlowClient
    from core.config import Config, SERVER_CHOICES, normalize_url, save_config


@dataclass
class SetupWizardResult:
    saved: bool
    config: Config | None = None


class SetupWizard:
    """Simple Tkinter first-run configuration flow."""

    def __init__(self, *, config_path=None) -> None:
        self.config_path = config_path
        self._result = SetupWizardResult(saved=False)

    def run(self) -> SetupWizardResult:
        try:
            import tkinter as tk
            from tkinter import ttk
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("tkinter is required for the setup wizard") from exc

        root = tk.Tk()
        root.title("VetFlowConnect - Konfiguracja")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

        frame = ttk.Frame(root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")

        api_key_var = tk.StringVar()
        server_var = tk.StringVar(value=SERVER_CHOICES[0][1])
        custom_var = tk.StringVar()
        status_var = tk.StringVar(value="Status: Oczekiwanie...")
        busy = {"value": False}

        ttk.Label(frame, text="VetFlowConnect - Konfiguracja").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Klucz API:").grid(row=1, column=0, sticky="w")
        api_entry = ttk.Entry(frame, textvariable=api_key_var, width=36, show="*")
        api_entry.grid(row=1, column=1, columnspan=2, sticky="we", pady=(0, 12))

        ttk.Label(frame, text="Serwer:").grid(row=2, column=0, sticky="nw")

        row_index = 2
        for label, value in SERVER_CHOICES[:-1]:
            row_index += 1
            ttk.Radiobutton(frame, text=label, value=value, variable=server_var).grid(row=row_index, column=1, columnspan=2, sticky="w")

        row_index += 1
        ttk.Radiobutton(frame, text="Custom", value="custom", variable=server_var).grid(row=row_index, column=1, sticky="w")
        custom_entry = ttk.Entry(frame, textvariable=custom_var, width=28)
        custom_entry.grid(row=row_index, column=2, sticky="we")

        button = ttk.Button(frame, text="Connect & Save")
        button.grid(row=row_index + 1, column=1, columnspan=2, sticky="e", pady=(12, 8))
        ttk.Label(frame, textvariable=status_var).grid(row=row_index + 2, column=0, columnspan=3, sticky="w")

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        def set_status(message: str) -> None:
            root.after(0, lambda: status_var.set(f"Status: {message}"))

        def set_busy(value: bool) -> None:
            def apply() -> None:
                busy["value"] = value
                state = "disabled" if value else "normal"
                api_entry.configure(state=state)
                custom_entry.configure(state=state)
                button.configure(state=state)
            root.after(0, apply)

        def selected_url() -> str:
            if server_var.get() == "custom":
                return custom_var.get().strip()
            return server_var.get().strip()

        def connect_and_save() -> None:
            if busy["value"]:
                return

            api_key = api_key_var.get().strip()
            url_raw = selected_url()
            if not api_key:
                set_status("Wpisz klucz API.")
                return
            if not url_raw:
                set_status("Wybierz serwer lub wpisz URL.")
                return

            set_busy(True)
            set_status("Laczenie...")

            def worker() -> None:
                try:
                    url = normalize_url(url_raw)
                    client = VetFlowClient(url, api_key)
                    asyncio.run(client.register_device())
                    asyncio.run(client.get_device_config())
                    config = Config(api_key=api_key, url=url)
                    save_config(config, self.config_path)
                    self._result = SetupWizardResult(saved=True, config=config)
                    set_status("Polaczono. Zapisano konfiguracje.")
                    root.after(250, root.destroy)
                except Exception as exc:
                    set_status(str(exc))
                finally:
                    set_busy(False)

            threading.Thread(target=worker, daemon=True).start()

        button.configure(command=connect_and_save)
        api_entry.focus_set()
        root.mainloop()
        return self._result


def run_setup_wizard(*, config_path=None) -> SetupWizardResult:
    return SetupWizard(config_path=config_path).run()
