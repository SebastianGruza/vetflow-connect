"""System tray integration for VetFlowConnect using pystray."""

from __future__ import annotations

import logging
import os
import sys
from typing import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("vetflow_connect")

COLOR_GREEN = "#22c55e"
COLOR_RED = "#ef4444"
COLOR_YELLOW = "#f59e0b"


def create_status_icon(color: str) -> Image.Image:
    """Create a 64x64 status icon — colored circle with 'V' letter."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill=color)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((size // 2, size // 2), "V", fill="white", anchor="mm", font=font)
    return img


class TrayApp:
    """System tray icon for VetFlowConnect."""

    def __init__(self, on_quit: Callable, log_file: str | None = None) -> None:
        self._on_quit = on_quit
        self._log_file = log_file
        self._status_text = "Uruchamianie..."
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: f"Status: {self._status_text}",
                None,
                enabled=False,
            ),
            pystray.MenuItem("Pokaż logi", self._show_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Zamknij", self._quit),
        )

    def _show_logs(self) -> None:
        if not self._log_file or not os.path.exists(self._log_file):
            return
        if sys.platform == "win32":
            os.startfile(self._log_file)  # noqa: S606
        else:
            import subprocess

            subprocess.Popen(["xdg-open", self._log_file])  # noqa: S603, S607

    def _quit(self) -> None:
        logger.info("Tray: quit requested")
        self._on_quit()
        if self._icon:
            self._icon.stop()

    def set_status(self, ok: bool, text: str | None = None) -> None:
        """Update tray icon color and status text."""
        self._status_text = text or ("Nasłuchuje" if ok else "Błąd połączenia")
        color = COLOR_GREEN if ok else COLOR_RED
        if self._icon:
            self._icon.icon = create_status_icon(color)
            self._icon.update_menu()

    def notify(self, title: str, message: str) -> None:
        """Show a balloon notification."""
        if self._icon:
            self._icon.notify(message, title)

    def run(self, setup: Callable | None = None) -> None:
        """Run tray icon on the current thread (must be main thread on Windows)."""
        self._icon = pystray.Icon(
            name="VetFlowConnect",
            icon=create_status_icon(COLOR_YELLOW),
            title="VetFlowConnect",
            menu=self._build_menu(),
        )
        self._icon.run(setup=setup)
