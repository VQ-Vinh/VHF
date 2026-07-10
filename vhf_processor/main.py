from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from vhf_processor.config.schema import load_config
from vhf_processor.gemini.prompt_builder import LANGUAGE_NAMES
from vhf_processor.pipeline.orchestrator import PipelineOrchestrator
from vhf_processor.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)

LANGUAGES = dict(sorted(LANGUAGE_NAMES.items()))
LANG_LIST = list(LANGUAGES.items())

_dot_count = 0
_was_recording: bool | None = None


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
                from vhf_processor.audio.wasapi_backend import WASAPIBackend
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


def print_banner() -> None:
    print("=" * 60)
    print("  VHF Radio Processor / Gemini 2.5")
    print("=" * 60)


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


def print_status(orc: PipelineOrchestrator) -> None:
    global _dot_count, _was_recording
    status = orc.get_status()
    seq = status["sequences_processed"]
    recording = status["recording"]

    if recording:
        if _was_recording is not True:
            if _was_recording is not None:
                print()
            print(f"  Recording.", end="", flush=True)
            _dot_count = 1
        else:
            _dot_count += 1
            print(f".", end="", flush=True)
        _was_recording = True
    else:
        if _was_recording is not False:
            if _was_recording is True:
                print()
            print(f"  Seq: {seq}  Listening...", flush=True)
            _was_recording = False
            _dot_count = 0


def apply_target(config, target: str | None) -> None:
    if target:
        config.translation.target_language = target


async def run_realtime(config_path: Path, target: str | None = None, capture_mode: str = "device", device_index: int = -1) -> None:
    config = load_config(config_path)
    apply_target(config, target)
    config.audio.capture_mode = capture_mode
    if device_index >= 0:
        config.audio.device_index = device_index
    setup_logger(level=config.general.log_level, console_level="WARNING")

    tgt = config.translation.target_language
    print_banner()
    print(f"  Target: {LANGUAGES.get(tgt, tgt)}  |  Source: auto-detect")
    print(f"  Capture: {config.audio.capture_mode}")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    logger.info("Starting real-time VHF processor", extra={"config": str(config_path), "target": tgt})

    orchestrator = PipelineOrchestrator(config)

    try:
        orchestrator.start()
        while True:
            print_status(orchestrator)
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Shutting down...")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main loop", exc_info=e)
    finally:
        orchestrator.stop()
        s = orchestrator.get_status()
        print(f"\n  Stopped. Session: {s['session_id']}, Processed: {s['sequences_processed']}")


def run_batch(config_path: Path, files: list[Path], target: str | None = None) -> None:
    config = load_config(config_path)
    apply_target(config, target)
    setup_logger(level=config.general.log_level, console_level="WARNING")

    tgt = config.translation.target_language
    print_banner()
    print(f"  Target: {LANGUAGES.get(tgt, tgt)}  |  Batch: {len(files)} file(s)")
    print("=" * 60)

    orchestrator = PipelineOrchestrator(config)
    orchestrator.start_session()

    for f in files:
        if not f.exists():
            logger.warning(f"Skipping: {f} not found")
            continue
        result = orchestrator.process_file(f)
        status = "OK" if not result.has_error else f"ERR: {result.error}"
        print(f"  [{status}] {f.name} -> {result.detected_language.upper() or '?'} conf={result.confidence:.0%}")

    orchestrator.stop()
    s = orchestrator.get_status()
    print(f"\n  Done. Files: {len(files)}, Session: {s['session_id']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VHF Radio Processor / Gemini 2.5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  main.py                    Real-time mode (default config)\n"
               "  main.py -t vi             Real-time, output Vietnamese\n"
               "  main.py -t ja batch *.wav Batch process, output Japanese\n"
               "  main.py --list-languages   List supported languages",
    )
    parser.add_argument(
        "-t", "--target",
        choices=list(LANGUAGES),
        help="Target output language (default: prompt)",
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Launch desktop GUI",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported languages and exit",
    )
    parser.add_argument(
        "batch",
        nargs="*",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    args = parse_args(sys.argv[1:])

    if args.list_languages:
        print("Supported languages:")
        for code, name in LANGUAGES.items():
            print(f"  {code}: {name}")
        return

    use_gui = args.gui or sys.stdin is None
    target = args.target
    if args.batch and args.batch[0] == "batch":
        files = [Path(a) for a in args.batch[1:]]
        if not files:
            print("Usage: main.py [-t <lang>] batch <file1.wav> ...")
            sys.exit(1)
        if not target:
            target = select_language()
        run_batch(Path("vhf_processor/config/default.toml"), files, target)
        return

    if use_gui:
        if sys.stdin is not None:
            try:
                mode, dev_idx = select_capture_mode()
                if not target:
                    target = select_language()
            except (EOFError, OSError, RuntimeError):
                mode, dev_idx = "device", -1
                target = target or "en"
        else:
            mode, dev_idx = "device", -1
            target = target or "en"

        from vhf_processor.gui.app import run_gui
        run_gui(
            capture_mode=mode,
            device_index=dev_idx,
            target_language=target,
        )
        return

    mode, dev_idx = select_capture_mode()
    if not target:
        target = select_language()

    try:
        if args.batch:
            config_path = Path(args.batch[0])
            if not config_path.exists():
                print(f"Config not found: {config_path}")
                sys.exit(1)
            asyncio.run(run_realtime(config_path, target, mode, dev_idx))
        else:
            asyncio.run(run_realtime(Path("vhf_processor/config/default.toml"), target, mode, dev_idx))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
