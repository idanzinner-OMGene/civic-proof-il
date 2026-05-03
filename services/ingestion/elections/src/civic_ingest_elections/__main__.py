"""CLI entry point: ``python -m civic_ingest_elections run``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
