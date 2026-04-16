"""Semctx version helpers."""

from importlib.metadata import PackageNotFoundError, version

from beartype import beartype

PACKAGE_NAME = "semctx"
__version__ = "0.1.0"


@beartype
def get_version() -> str:
    """Return the installed package version or fallback version."""
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return __version__
