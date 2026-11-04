"""Parsers for alternative-splicing tool outputs.

EpitopeRank accepts **rMATS input only**. The rMATS junction-count tables
(``SE/A3SS/A5SS/MXE/RI.MATS.JC.txt``) are normalized into the standardized
``AS_event_master`` contract, which is the internal interchange format used by
the rest of the pipeline.

Vendor exports (e.g. BGI per-sample rMATS ``.xls``) reach the same contract
through the ingestion adapter (:mod:`epitoperank.data.ingestion`), not through a
second parser.

SUPPA2 / MAJIQ / LeafCutter / pre-computed delta-PSI tables used to be
supported; those parsers were removed so there is exactly one input contract
to validate, test and document.
"""

from epitoperank.splicing.parsers.rmats import (
    RMATS_EVENT_FILES,
    is_rmats_directory,
    parse_rmats_directory,
    parse_rmats_file,
)

__all__ = [
    "RMATS_EVENT_FILES",
    "is_rmats_directory",
    "parse_rmats_directory",
    "parse_rmats_file",
]
