import csv

import pytest

from epitoperank.neoantigen import junction_peptides, run, translate, predict_iedb
from urllib.parse import parse_qs
from io import BytesIO
from epitoperank.splicing.schema import CORE_EVENT_FIELDS


def test_translation_and_junction_candidates() -> None:
    assert translate('ATGGCTTAA') == 'MA'
    with pytest.raises(ValueError):
        translate('ATGN')
    reference = 'ATG' + 'GCT' * 20
    altered = 'ATG' + 'GCT' * 6 + 'TGG' * 8
    peptides = junction_peptides(reference, altered, 21)
    assert peptides
    protein = translate(altered)
    for item in peptides:
        start = item['start_aa'] - 1
        assert start < item['junction_aa'] < start + item['length']
        assert item['peptide'] == protein[start:start + item['length']]
        assert item['peptide'] not in translate(reference)


def test_run_links_event_and_preserves_prediction_provenance(tmp_path) -> None:
    source = tmp_path / 'source'; source.mkdir()
    event = dict.fromkeys(CORE_EVENT_FIELDS, '')
    event.update(event_id='SE:1', gene_id='G1', gene_symbol='GENE1', event_type='SE',
                 chromosome='chr1', strand='+', genomic_coordinates='chr1:10-20',
                 coordinate_system='1-based-inclusive', source_tool='rMATS', FDR='0.01')
    with (source/'AS_event_master.tsv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter='\t')
        writer.writeheader(); writer.writerow(event)
    with (source/'splice_orfs.tsv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, delimiter='\t')
        writer.writerow(['event_id','reference_cds','altered_cds','junction_nt'])
        writer.writerow(['SE:1','ATG'+'GCT'*20,'ATG'+'GCT'*6+'TGG'*8,21])
        writer.writerow(['SE:missing','ATG','ATG',3])
    result = run(source, source/'splice_orfs.tsv', tmp_path/'out', alleles=['HLA-A*02:01'],
                 predictor=lambda peptide, allele: {'peptide': peptide, 'allele': allele, 'percentile_rank': '0.4'})
    assert result['candidate_count'] > 0
    assert result['prediction_count'] > 0
    assert result['prediction_method'] == 'IEDB NetMHCpan 4.1 EL'
    assert result['prediction_attempt_count'] == result['prediction_count']
    assert result['skipped'][0]['reason'] == 'event_id not found'
    with (tmp_path/'out'/'splice_peptides.tsv').open(encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    assert all(row['event_id'] == 'SE:1' and row['fdr'] == '0.01' for row in rows)


@pytest.mark.parametrize('junction', [19, 20, 21])
def test_junction_phases_and_whitespace(junction):
    reference = 'ATG' + 'GCT' * 20
    altered = 'ATG' + 'GCT' * 6 + 'TGG' * 8
    expected = junction_peptides(reference, altered, junction)
    assert expected
    assert junction_peptides(reference, '  ' + altered + '  ', junction) == expected
    for item in expected:
        start = (item['start_aa'] - 1) * 3
        assert start < junction < start + item['length'] * 3


def test_txt_input_and_incomplete_rows(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    event = dict.fromkeys(CORE_EVENT_FIELDS, '')
    event.update(event_id='SE:1', gene_id='G1', gene_symbol='G', event_type='SE',
                 chromosome='chr1', strand='+', genomic_coordinates='chr1:10-20',
                 coordinate_system='1-based-inclusive', source_tool='rMATS')
    with (source / 'AS_event_master.tsv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=CORE_EVENT_FIELDS, delimiter='\t')
        writer.writeheader(); writer.writerow(event)
    table = source / 'coding_pairs.txt'
    table.write_text(' event_id \treference_cds\taltered_cds\tjunction_nt\n'
                     'SE:1\tATG\n'
                     + 'SE:1\t' + 'ATG' + 'GCT' * 20 + '\t' + 'ATG' + 'GCT' * 6 + 'TGG' * 8 + '\t21\n', encoding='utf-8')
    result = run(source, table, tmp_path / 'out')
    assert result['candidate_count'] > 0
    assert len(result['skipped']) == 1


def test_iedb_request_uses_explicit_netmhcpan_version():
    def opener(request, timeout):
        params = parse_qs(request.data.decode())
        assert params['method'] == ['netmhcpan_el-4.1']
        assert params['allele'] == ['HLA-A*02:01']
        assert params['sequence_text'] == ['SLYNTVATL']
        return BytesIO(b'allele\tpeptide\tscore\tpercentile_rank\nHLA-A*02:01\tSLYNTVATL\t0.8\t0.06\n')
    result = predict_iedb('SLYNTVATL', 'HLA-A*02:01', opener=opener)
    assert result['percentile_rank'] == '0.06'
