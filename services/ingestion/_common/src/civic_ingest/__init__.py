"""civic_ingest — shared scaffolding for Phase-2 ingestion adapters.

Submodules:

* :mod:`civic_ingest.manifest` — Pydantic ``SourceManifest`` + YAML loader.
* :mod:`civic_ingest.queue` — Postgres-native ``jobs`` queue (SKIP LOCKED).
* :mod:`civic_ingest.orchestrator` — ``IngestRun`` context manager wrapping
  ``ingest_runs`` lifecycle rows.
"""

from __future__ import annotations

from .adapter import AdapterResult, run_adapter
from .csv_page import parse_csv_page
from .manifest import SourceManifest, load_manifest, load_all_manifests
from .mk_individual_lookup import (
    LookupUnresolved,
    MkIndividualLookup,
    load_mk_individual_lookup,
)
from .odata import ODataPage, parse_odata_page
from .orchestrator import IngestRun
from .queue import Job, claim_one, enqueue, mark_done, mark_failed

__all__ = [
    "AdapterResult",
    "IngestRun",
    "Job",
    "LookupUnresolved",
    "MkIndividualLookup",
    "ODataPage",
    "SourceManifest",
    "claim_one",
    "enqueue",
    "load_all_manifests",
    "load_manifest",
    "load_mk_individual_lookup",
    "mark_done",
    "mark_failed",
    "parse_csv_page",
    "parse_odata_page",
    "run_adapter",
]
