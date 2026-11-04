"""Run official moPepGen on rMATS JC tables with locally supplied references.

Outputs are proteomics-oriented variant peptides, not splice_orfs.tsv or
validated HLA epitopes. See docs/NEOANTIGEN.md before interpreting them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

IMAGE = 'ghcr.io/uclahs-cds/mopepgen@sha256:68b2a44eea775a80c5055890369f2376933681579d2fbb3cefa48d1f949d4b86'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def execute(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('se', 'a3ss', 'a5ss', 'mxe', 'ri'):
        parser.add_argument('--' + flag, type=Path)
    for flag in ('genome', 'gtf', 'proteome', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--reference-source', choices=('GENCODE', 'ENSEMBL'), required=True)
    parser.add_argument('--reference-version', required=True, help='Reference assembly and annotation release; supplied by user')
    args = parser.parse_args(argv)
    files = {key: getattr(args, key) for key in ('se', 'a3ss', 'a5ss', 'mxe', 'ri', 'genome', 'gtf', 'proteome') if getattr(args, key)}
    if not any(key in files for key in ('se', 'a3ss', 'a5ss', 'mxe', 'ri')):
        parser.error('at least one rMATS JC table is required')
    for key, value in files.items():
        value = value.resolve()
        if not value.is_file() or ',' in str(value):
            parser.error(f'{key} must be an existing file with no comma in its path')
        files[key] = value
    output = args.output.resolve()
    if output.exists() or ',' in str(output):
        parser.error('output must be a new path without commas')
    output.mkdir(parents=True)
    mounts = []
    container_paths = {}
    for key, path in files.items():
        suffix = '.gtf' if key == 'gtf' else '.fa' if key in ('genome', 'proteome') else '.txt'
        target = '/inputs/' + key + suffix
        container_paths[key] = target
        mounts.extend(['--mount', f'type=bind,src={path},dst={target},readonly'])
    base = ['docker', 'run', '--rm', '--network', 'none', *mounts,
            '--mount', f'type=bind,src={output},dst=/output', IMAGE, 'moPepGen']
    commands = [base + ['parseRMATS', *sum(([f'--{key}', container_paths[key]] for key in ('se', 'a3ss', 'a5ss', 'mxe', 'ri') if key in files), []),
                '-g', container_paths['genome'], '-a', container_paths['gtf'], '--reference-source', args.reference_source,
                '--source', 'rMATS', '-o', '/output/events.gvf'],
                base + ['callVariant', '-i', '/output/events.gvf', '-o', '/output/variant_peptides.fasta',
                '-g', container_paths['genome'], '-a', container_paths['gtf'], '-p', container_paths['proteome'],
                '--reference-source', args.reference_source]]
    manifest = {'image': IMAGE, 'reference_source': args.reference_source, 'reference_version_declared': args.reference_version,
                'inputs': {key: {'path': str(path), 'sha256': sha256(path)} for key, path in files.items()},
                'commands': commands, 'status': 'running',
                'limitations': ['Reference compatibility is declared by the user and not verified by the program.',
                                'Outputs use moPepGen default proteomics cleavage rules, not HLA-binding predictions.',
                                'Outputs are not a reference/altered CDS pair or evidence of tumor specificity.']}
    def save():
        (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    for index, command in enumerate(commands):
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
        except OSError as error:
            manifest.update(status='failed', error=str(error)); save(); return 1
        (output / f'step_{index+1}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            manifest.update(status='failed', failed_step=index+1, exit_code=result.returncode); save(); return result.returncode
    manifest['status'] = 'complete'
    manifest['output_sizes'] = {name: (output / name).stat().st_size for name in ('events.gvf', 'variant_peptides.fasta')}
    manifest['warnings'] = []
    if manifest['output_sizes']['variant_peptides.fasta'] == 0:
        manifest['warnings'].append('No variant peptides were generated; inspect logs and input/reference compatibility.')
    save()
    print(f'Results: {output}')
    return 0


if __name__ == '__main__':
    sys.exit(execute())
