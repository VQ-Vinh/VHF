"""Hide console windows created by subprocesses in the frozen Windows app.

PyInstaller's ``console=False`` hides the console of the main executable, but
console programs launched by dependencies (notably ``gcloud.cmd`` from
google-auth) can still briefly create their own windows.
"""

from __future__ import annotations

import subprocess
import sys


if sys.platform == "win32":
    _OriginalPopen = subprocess.Popen

    class _NoConsolePopen(_OriginalPopen):
        def __init__(self, *args, **kwargs):
            creationflags = kwargs.get("creationflags", 0)
            kwargs["creationflags"] = creationflags | subprocess.CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _NoConsolePopen
