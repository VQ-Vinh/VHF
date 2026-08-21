"""PyInstaller entry point for the Raspberry Pi station.

The console script installed by pip calls ``prana_linux.station:main``, but a
frozen bundle executes its entry file as a script. Pointing the spec straight at
``station.py`` therefore defined the functions and exited 0 without ever running
main(), leaving systemd with a service that started and immediately stopped.
"""

from prana_linux.station import main

if __name__ == "__main__":
    main()
