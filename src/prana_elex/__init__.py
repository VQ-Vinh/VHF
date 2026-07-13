from prana_elex.core.pipeline.events import event_bus


def cli():
    from prana_elex.app.cli import main
    main()


def desktop():
    from prana_elex.app.desktop import main
    main()


__all__ = ["event_bus", "cli", "desktop"]
