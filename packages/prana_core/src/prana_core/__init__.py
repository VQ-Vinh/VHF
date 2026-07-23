"""Shared, platform-neutral PRANA ELEX runtime."""

from importlib.resources import files

__version__ = files("prana_core").joinpath("VERSION").read_text(encoding="utf-8").strip()

__all__ = ["__version__"]
