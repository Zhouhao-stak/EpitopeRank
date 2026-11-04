from pathlib import Path

import pytest

from splicegaip.data.loader import Dataset
from splicegaip.splicing.schema import parse_event_row
from splicegaip.neoantigen_audit import audit, filter_events


def test_audit_does_not_infer_missing_evidence():
    ds = Dataset('x', Path('.'), 'standard', [parse_event_row({'event_id': 'a'})], [])
    result = audit(ds, {})
    assert result['requires_confirmation']
    assert result['declared_evidence']['normal_design'] is None
    assert result['missing']


def test_event_filter_requires_evidence_and_accounts_for_exclusions():
    def event(id, **fields):
        return parse_event_row({'event_id': id, 'FDR': '0.01', 'delta_PSI': '0.2',
                                'total_support_reads': '20', 'valid_sample_count': '4',
                                'single_sample_driven': 'false', 'mapping_ambiguity': 'false', **fields})
    ds = Dataset('x', Path('.'), 'standard', [event('pass'), event('fdr', FDR='0.05'),
                 event('unknown', mapping_ambiguity='')], [])
    with pytest.raises(ValueError):
        filter_events(ds, min_support=10, min_samples=2)
    result = filter_events(ds, min_support=10, min_samples=2, support_is_junction_reads=True)
    assert result['event_ids'] == ['pass']
    assert sum(result['excluded_reasons'].values()) + result['surviving_count'] == result['input_count']
