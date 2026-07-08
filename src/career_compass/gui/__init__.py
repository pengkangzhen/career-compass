"""北斗星 GUI entry."""

__all__ = ["main"]


def main() -> None:
    from .app import main as _main

    _main()
