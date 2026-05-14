"""Entry point: `python -m neo_makervigate`."""

from __future__ import annotations

import sys

from neo_makervigate.app import run


def main() -> int:
    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
