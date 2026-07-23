import multiprocessing
multiprocessing.freeze_support()

import os
import sys


def _redirect_stdio() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


_redirect_stdio()

from prana_windows.desktop import main

main()
