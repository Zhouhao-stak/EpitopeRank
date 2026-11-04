"""Peptide prediction layer for EpitopeRank.

Public entry points::

    from epitoperank.peptide import PeptideOptions, run, predict_peptides

    result = run(
        output_dir="out/peptides",
        input_dir="examples/demo_rmats",
        cds_table="examples/demo_rmats/splice_orfs.tsv",
        options=PeptideOptions(alleles=["HLA-A*02:01"], mhc_class="both"),
    )

The package is offline-first: properties, HLA handling, self-proteome
filtering and ranking run locally; only MHC binding/processing prediction
needs the IEDB service (or a local ``mhcflurry`` install).
"""

from __future__ import annotations

from .filters import SelfFilterResult, annotate_candidates, scan_proteomes
from .hla import (
    CLASS_I_PANEL,
    CLASS_II_PANEL,
    HlaAllele,
    HlaError,
    describe as describe_allele,
    parse_panel,
    panel,
)
from .iedb import (
    DEFAULT_METHODS,
    METHODS,
    IedbClient,
    IedbError,
    IedbResponseError,
    IedbUnavailable,
    method_table,
)
from .pipeline import (
    LIMITATIONS,
    PEPTIDE_FIELDS,
    PREDICTION_FIELDS,
    PeptideOptions,
    aggregate,
    candidates_from_cds,
    load_peptide_table,
    predict_peptides,
    run,
)
from .properties import describe, describe_many
from .scoring import DEFAULT_WEIGHTS, composite, describe as describe_scoring, rank
from .sequences import (
    AA_ALPHABET,
    MHC_I_LENGTHS,
    MHC_II_LENGTHS,
    SelfReference,
    SequenceError,
    normalize_peptide,
    read_fasta,
    validate_peptide,
)

__all__ = [
    "AA_ALPHABET",
    "CLASS_I_PANEL",
    "CLASS_II_PANEL",
    "DEFAULT_METHODS",
    "DEFAULT_WEIGHTS",
    "HlaAllele",
    "HlaError",
    "IedbClient",
    "IedbError",
    "IedbResponseError",
    "IedbUnavailable",
    "LIMITATIONS",
    "METHODS",
    "MHC_I_LENGTHS",
    "MHC_II_LENGTHS",
    "PEPTIDE_FIELDS",
    "PREDICTION_FIELDS",
    "PeptideOptions",
    "SelfFilterResult",
    "SelfReference",
    "SequenceError",
    "aggregate",
    "annotate_candidates",
    "candidates_from_cds",
    "capabilities",
    "composite",
    "describe",
    "describe_allele",
    "describe_many",
    "describe_scoring",
    "load_peptide_table",
    "method_table",
    "normalize_peptide",
    "panel",
    "parse_panel",
    "predict_peptides",
    "rank",
    "read_fasta",
    "run",
    "scan_proteomes",
    "validate_peptide",
]


def capabilities() -> dict[str, object]:
    """Describe which peptide features can run right now.

    Used by the API, the report and the agent before it decides to call a
    network service.
    """
    from . import local_models, reference

    return {
        "predictors": {
            "iedb": {
                "available": True,
                "requires": "internet access to tools.iedb.org / query-api.iedb.org",
                "tools": sorted({spec.tool for spec in METHODS.values()}),
            },
            "mhcflurry": local_models.status(),
        },
        "mhc_classes": [1, 2],
        "methods": method_table(),
        "reference": reference.summary().as_dict(),
        "ranking": describe_scoring(),
        "limits": {
            "max_predictions_per_run": 2000,
            "max_sequences_per_iedb_request": 100,
            "mhc_i_lengths": list(MHC_I_LENGTHS),
            "mhc_ii_lengths": list(MHC_II_LENGTHS),
        },
        "interpretation": (
            "Binding prediction is not antigen presentation and not "
            "immunogenicity; see docs/PEPTIDE.md."
        ),
    }
