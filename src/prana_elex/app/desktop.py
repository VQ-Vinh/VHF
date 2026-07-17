from __future__ import annotations

import sys
from pathlib import Path

from prana_elex.config.schema import load_config
from prana_elex.common.languages import LANGUAGE_NAMES
from prana_elex.ui.app import run_app
from prana_elex.common.logger import get_logger

logger = get_logger(__name__)

LANGUAGES = dict(sorted(LANGUAGE_NAMES.items()))
LANG_LIST = list(LANGUAGES.items())


def select_capture_mode() -> tuple[str, int]:
    print()
    print("  Select capture mode:")
    print("    1. Device      (USB SoundCard / microphone input)")
    print("    2. Loopback    (capture system audio output)")
    print()
    while True:
        choice = input("  Choice (1-2): ").strip()
        if choice == "1":
            return ("device", -1)
        if choice == "2":
            try:
                from prana_elex.audio.wasapi import WASAPIBackend
                devices = WASAPIBackend.list_loopback_devices()
            except ImportError:
                devices = []
            if not devices:
                print("  Loopback not supported on this platform.")
                continue
            print()
            print("  Available loopback devices:")
            for i, d in enumerate(devices, 1):
                print(f"    {i}. [{d['index']}] {d['name']}")
            print()
            while True:
                try:
                    pick = input(f"  Choice (1-{len(devices)}): ").strip()
                    idx = int(pick) - 1
                    if 0 <= idx < len(devices):
                        return ("loopback", devices[idx]["index"])
                except ValueError:
                    pass
                print(f"  Invalid. Enter 1-{len(devices)}.")
        print("  Invalid. Enter 1 or 2.")


def select_language() -> str:
    print()
    print("  Select output language:")
    for i, (code, name) in enumerate(LANG_LIST, 1):
        print(f"    {i}. {name} ({code})")
    print()
    while True:
        try:
            choice = input(f"  Choice (1-{len(LANG_LIST)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(LANG_LIST):
                return LANG_LIST[idx][0]
        except ValueError:
            pass
        print(f"  Invalid. Enter 1-{len(LANG_LIST)}.")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    has_stdin = sys.stdin is not None
    if has_stdin:
        try:
            mode, dev_idx = select_capture_mode()
            target = select_language()
        except (EOFError, OSError, RuntimeError):
            mode, dev_idx = "device", -1
            target = "en"
    else:
        mode, dev_idx = "device", -1
        target = "en"

    run_app(
        capture_mode=mode,
        device_index=dev_idx,
        target_language=target,
    )


if __name__ == "__main__":
    main()
