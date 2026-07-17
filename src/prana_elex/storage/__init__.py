__all__ = ["LocalStorage"]


def __getattr__(name: str):
    if name == "LocalStorage":
        from prana_elex.storage.local import LocalStorage

        return LocalStorage
    raise AttributeError(name)
