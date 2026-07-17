def cli():
    from prana_elex.app.cli import main
    main()


def desktop():
    from prana_elex.app.desktop import main
    main()


__all__ = ["cli", "desktop"]
