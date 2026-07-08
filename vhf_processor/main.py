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
    status = orc.get_status()
    state = "[RECORDING]" if status["recording"] else "[LISTENING]"
    print(
        f"  [{status['session_id']}] "
        f"Seq: {status['sequences_processed']} | "
        f"{state}",
        flush=True,
    )


def apply_target(config, target: str | None) -> None:
    if target:
        config.translation.target_language = target


async def run_realtime(config_path: Path, target: str | None = None) -> None:
    config = load_config(config_path)
    apply_target(config, target)
    setup_logger(level=config.general.log_level, console_level="WARNING")

    tgt = config.translation.target_language
    print_banner()
    print(f"  Target: {LANGUAGES.get(tgt, tgt)}  |  Source: auto-detect")
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    logger.info("Starting real-time VHF processor", extra={"config": str(config_path), "target": tgt})

    orchestrator = PipelineOrchestrator(config)

    try:
        orchestrator.start()
        while True:
            print_status(orchestrator)
            await asyncio.sleep(5)

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

    target = args.target
    if args.batch and args.batch[0] == "batch":
        files = [Path(a) for a in args.batch[1:]]
        if not files:
            print("Usage: main.py [-t <lang>] batch <file1.wav> ...")
            sys.exit(1)
        if not target:
            target = select_language()
        run_batch(Path("vhf_processor/config/default.toml"), files, target)
    elif args.batch:
        config_path = Path(args.batch[0])
        if not config_path.exists():
            print(f"Config not found: {config_path}")
            sys.exit(1)
        if not target:
            target = select_language()
        asyncio.run(run_realtime(config_path, target))
    else:
        if not target:
            target = select_language()
        asyncio.run(run_realtime(Path("vhf_processor/config/default.toml"), target))


if __name__ == "__main__":
    main()
