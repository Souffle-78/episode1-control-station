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
    p.add_argument("--connect-test", metavar="PORT", help="connect the real SLCAN backend and print a snapshot, then exit")
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

    if args.connect_test:
        from episode1_app.backend import SlcanBackend

        backend = SlcanBackend()
        errors: list[str] = []
        backend.error.connect(errors.append)

        def probe() -> None:
            try:
                backend.connect_device(args.connect_test)
                for _ in range(20):
                    app.processEvents()
                snap = backend.snapshot()
                print("CONNECTED", backend.connected, "VOLTAGE", snap.voltage, "JOINTS", len(snap.joints))
                for j in snap.joints:
                    print(j.index, j.name, round(j.angle, 2), j.enabled, j.status)
                if errors:
                    print("ERRORS", errors)
                backend.disconnect_device()
            except Exception as exc:
                print("CONNECT_FAILED", type(exc).__name__, exc)
            finally:
                backend.shutdown()
                app.quit()

        QTimer.singleShot(100, probe)
        return app.exec()

    backend = DemoBackend()
    win = MainWindow(backend=backend, demo=True)
    if args.size and "x" in args.size and args.screenshot:
        w, h = (int(x) for x in args.size.lower().split("x", 1))
        win.resize(w, h)
    elif not args.screenshot:
        screen = app.primaryScreen().availableGeometry()
        win.resize(min(1360, max(1180, screen.width() - 40)),
                   min(860, max(760, screen.height() - 40)))
        win.move(screen.x() + (screen.width() - win.width()) // 2,
                 screen.y() + (screen.height() - win.height()) // 2)
    win.show()

    if (args.demo or args.screenshot) and not backend.connected:
        if win.port.currentText().strip().upper() != "DEMO":
            win.port.setCurrentText("DEMO")
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
