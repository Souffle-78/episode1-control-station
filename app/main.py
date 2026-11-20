#!/usr/bin/env python3
"""Episode 1 · Arm Control Station — MVP entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from episode1_app.backend import DemoBackend
from episode1_app.theme import apply_theme
from episode1_app.window import MainWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Episode 1 arm control station")
    p.add_argument("--demo", action="store_true", help="auto-connect the demo backend")
    p.add_argument("--screenshot", type=Path, help="render one frame to a PNG and exit")
    p.add_argument("--size", default="1440x900", help="window size for screenshot")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Episode 1 Control Station")
    app.setOrganizationName("TSU Robotics")
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon = base / "assets" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    apply_theme(app)

    backend = DemoBackend()
    win = MainWindow(backend=backend, demo=True)
    if args.size and "x" in args.size and args.screenshot:
        w, h = (int(x) for x in args.size.lower().split("x", 1))
        win.resize(w, h)
    win.show()

    if args.demo or args.screenshot:
        backend.connect_device("DEMO")

    if args.screenshot:
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)

        def capture() -> None:
            app.processEvents()
            pix = win.grab()
            pix.save(str(args.screenshot))
            print(f"wrote {args.screenshot} ({pix.width()}x{pix.height()})")
            app.quit()

        QTimer.singleShot(700, capture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
