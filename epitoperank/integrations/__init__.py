"""Optional open-source backends that strengthen EpitopeRank.

Each backend wraps a third-party library that is *not* a hard dependency of
the platform:

* :mod:`epitoperank.integrations.enrichr`  — GSEApy/Enrichr over-representation
  analysis (GO / KEGG / Reactome / MSigDB) instead of hand-rolled HTTP calls;
* :mod:`epitoperank.integrations.mygene_client` — the official MyGene.info
  client for gene annotation.

Everything here is defensive: a missing library, a network failure or a
timeout returns ``None`` and the caller falls back to the built-in
implementation. The agent must never break because an optional component
is unavailable.
"""

from __future__ import annotations

from epitoperank.integrations.capabilities import (
    Capability,
    available_backends,
    capabilities,
    capability_report,
    has_backend,
)

__all__ = [
    "Capability",
    "available_backends",
    "capabilities",
    "capability_report",
    "has_backend",
]
