import multiprocessing

from prana_windows.station import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
