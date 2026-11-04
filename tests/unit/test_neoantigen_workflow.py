from pathlib import Path

import pytest

from epitoperank.data.loader import Dataset
from epitoperank.splicing.schema import parse_event_row
from epitoperank.neoantigen_workflow import start, advance


def test_stages_require_confirmation_and_stop_on_empty_filter(tmp_path):
    event = parse_event_row({'event_id': 'x', 'FDR': '0.5', 'delta_PSI': '0.2'})
    ds = Dataset('x', tmp_path, 'standard', [event], [])
    state = start(ds, {})
    with pytest.raises(ValueError, match='确认'):
        advance(state, ds, {})
    state = advance(state, ds, {'confirm': True, 'input_is_quantified_events': True, 'event_set': 'unknown'})
    state = advance(state, ds, {'confirm': True, 'min_support': 10, 'min_samples': 2, 'support_is_junction_reads': True})
    assert state['stopped']
    with pytest.raises(ValueError, match='已停止'):
        advance(state, ds, {'confirm': True})


def test_changed_data_invalidates_audit(tmp_path):
    ds = Dataset('x', tmp_path, 'standard', [parse_event_row({'event_id': 'x'})], [])
    state = start(ds, {})
    ds.events.append(parse_event_row({'event_id': 'y'}))
    with pytest.raises(ValueError, match='已更改'):
        advance(state, ds, {'confirm': True})


def test_staged_workflow_requires_explicit_gap_and_builds_report(tmp_path):
    event = parse_event_row({'event_id':'x', 'gene_symbol':'GENE', 'FDR':'0.01', 'delta_PSI':'0.2',
                             'total_support_reads':'20', 'valid_sample_count':'3',
                             'single_sample_driven':'false', 'mapping_ambiguity':'false'})
    ds = Dataset('x', tmp_path, 'standard', [event], [])
    orf = tmp_path / 'orfs.tsv'
    orf.write_text('event_id\treference_cds\taltered_cds\tjunction_nt\torf_source\tframe_status\tpremature_stop\n'
                   + 'x\t' + 'ATG' + 'GCT' * 20 + '\t' + 'ATG' + 'GCT' * 6 + 'TGG' * 8 + '\t21\tupstream\tin_frame\tno\n')
    for name in ('paired.fa', 'gtex.fa', 'proteome.fa'):
        (tmp_path / name).write_text('>normal\nGGGGGGGGGGGG\n')
    state = start(ds, {})
    state = advance(state, ds, {'confirm':True, 'input_is_quantified_events':True, 'event_set':'unknown'})
    state = advance(state, ds, {'confirm':True, 'min_support':10, 'min_samples':2, 'support_is_junction_reads':True})
    state = advance(state, ds, {'confirm':True, 'orf_file':'orfs.tsv'})
    params = {'confirm':True, 'protein_fastas':{'paired_normal':'paired.fa','gtex':'gtex.fa','proteome':'proteome.fa'}}
    with pytest.raises(ValueError, match='连接点表'):
        advance(state, ds, params)
    state = advance(state, ds, {**params, 'acknowledge_missing_gtex_junction_and_tissue_expression':True})
    state = advance(state, ds, {'confirm':True, 'expression_records':{'x':{'expression':1,'expression_unit':'TPM'}}})
    state = advance(state, ds, {'confirm':True, 'alleles':['HLA-A*02:01'], 'hla_source':'WES', 'hla_confidence':'verified'},
                    predictor=lambda peptide, allele: {'percentile_rank':'0.5'})
    state = advance(state, ds, {'confirm':True})
    assert len(state['history'][-1]['sections']) == 6
    assert state['history'][-1]['sections']['候选表']
