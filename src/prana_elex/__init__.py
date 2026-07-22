def cli():
    from prana_elex.app.cli import main
    main()


def desktop():
    from prana_elex.app.desktop import main
    main()


def station():
    from prana_elex.app.station import main
    main()


def station_provision():
    from prana_elex.app.station_provision import main
    main()


__all__ = ["cli", "desktop", "station", "station_provision"]
