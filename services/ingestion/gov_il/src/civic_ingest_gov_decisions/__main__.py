"""Allow ``python -m civic_ingest_gov_decisions``."""

import sys

from .cli import main

sys.exit(main())
