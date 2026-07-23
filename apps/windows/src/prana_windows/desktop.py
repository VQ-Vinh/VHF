"""Windows Qt desktop composition entrypoint."""

from prana_windows.ui.app import run_app


def main() -> None:
    """Start the Windows UI without invoking the CLI capture prompts."""
    run_app()


if __name__ == "__main__":
    main()
