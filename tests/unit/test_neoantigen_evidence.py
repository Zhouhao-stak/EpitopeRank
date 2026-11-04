import pytest

from epitoperank.neoantigen_evidence import normal_protein_filter, expression_evidence, supplied_orf_candidates, assess_nmd, gtex_junction_filter, normal_tissue_expression


def test_normal_databases_are_required_and_accounted(tmp_path):
    candidates = [{'peptide': 'AAAAAAAA'}, {'peptide': 'WWWWWWWW'}, {'peptide': 'GGGGGGGG'}]
    with pytest.raises(ValueError):
        normal_protein_filter(candidates, {})
    databases = {}
    for name, sequence in [('paired_normal', 'MAAAAAAAAK'), ('gtex', 'KWWWWWWWWK'), ('proteome', 'MKKKKKKK')]:
        path = tmp_path / (name + '.fa')
        path.write_text('>p\n' + sequence + '\n', encoding='utf-8')
        databases[name] = path
    result = normal_protein_filter(candidates, databases)
    assert [c['peptide'] for c in result['candidates']] == ['GGGGGGGG']
    assert [stage['surviving_count'] for stage in result['stages']] == [2, 1, 1]
    assert len(result['stages'][0]['sha256']) == 64


def test_expression_and_recurrence_are_distinct():
    candidates = [{'event_id': 'a'}, {'event_id': 'b'}, {'event_id': 'c'}]
    result = expression_evidence(candidates, {'a': {'expression': 1, 'expression_unit': 'TPM', 'recurrence_count': 1, 'recurrence_total': 10},
                                               'b': {'expression': 0, 'expression_unit': 'TPM'}})
    assert result['surviving_count'] == 1
    assert result['candidates'][0]['recurrence'] == 0.1
    assert sum(result['excluded_reasons'].values()) == 2


def test_orf_requires_provenance_and_separates_early_stops():
    row = {'event_id': 'a', 'reference_cds': 'ATG' + 'GCT' * 20,
           'altered_cds': 'ATG' + 'GCT' * 6 + 'TGG' * 8, 'junction_nt': 21,
           'orf_source': 'reconstructed upstream', 'frame_status': 'in_frame', 'premature_stop': 'no'}
    result = supplied_orf_candidates([row, {**row, 'orf_source': ''}], {'a'})
    assert result['surviving_count'] == 1 and result['candidates']
    stopped = {**row, 'altered_cds': row['altered_cds'] + 'TAA' + 'GCT', 'premature_stop': 'yes'}
    result = supplied_orf_candidates([stopped], {'a'})
    assert result['separated'] and not result['candidates']


def test_nmd_distance_and_missing_junction():
    cds = 'ATG' + 'TAA' + 'GCT' * 3
    assert assess_nmd(cds, 'yes', 57)['status'] == 'candidate'
    assert assess_nmd(cds, 'yes', 56)['status'] == 'not_predicted'
    assert assess_nmd(cds, 'yes', None)['status'] == 'unknown'


def test_junction_and_normal_expression_evidence(tmp_path):
    event = tmp_path / 'events.tsv'; event.write_text('event_id\tchromosome\tintron_start\tintron_end\tstrand\na\tchr1\t10\t20\t+\nb\tchr1\t30\t40\t-\n')
    gtex = tmp_path / 'gtex.tsv'; gtex.write_text('chromosome\tintron_start\tintron_end\tstrand\nchr1\t10\t20\t+\n')
    candidates = [{'event_id':'a'}, {'event_id':'b'}]
    with pytest.raises(ValueError, match='版本'):
        gtex_junction_filter(candidates, event, gtex, event_build='GRCh38', gtex_build='hg19')
    filtered = gtex_junction_filter(candidates, event, gtex, event_build='GRCh38', gtex_build='GRCh38')
    assert filtered['candidates'] == [{'event_id':'b'}]
    expr = tmp_path / 'expr.tsv'; expr.write_text('gene_id\ttissue\texpression\tunit\nG1\theart\t2.5\tTPM\n')
    result = normal_tissue_expression(filtered['candidates'], {'b':'G1'}, expr)
    assert result['candidates'][0]['normal_tissue_expression'][0]['expression'] == 2.5
