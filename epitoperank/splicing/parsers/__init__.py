"""Parsers for alternative-splicing tool outputs.

Each parser converts a tool-specific output table into the standardized
``AS_event_master`` contract. Currently supported:

* rMATS (JC tables)                 -- :mod:`epitoperank.splicing.parsers.rmats`
* SUPPA2 (``.psv`` / ``.ioe``)      -- :mod:`epitoperank.splicing.parsers.suppa`
* MAJIQ (``.majiq``-derived TSV)    -- :mod:`epitoperank.splicing.parsers.majiq`
* LeafCutter (``_cluster_significance.txt``) -- :mod:`epitoperank.splicing.parsers.leafcutter`
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
