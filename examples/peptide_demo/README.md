# Peptide prediction demo

- `peptides.tsv`: real IEDB assay records (peptide, recorded HLA restriction, recorded assay outcome). The assay outcome is **not** a binding benchmark.
- `AS_event_master.tsv` + `splice_orfs.tsv`: a **synthetic positive control**. The altered CDS encodes a real epitope across a synthetic junction; reference CDS, coordinates, gene names and PSI values are placeholders. Do not interpret these events biologically.

Run prediction only:

```bash
python run.py peptide --peptides examples/peptide_demo/peptides.tsv \
  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_demo
```

Run the splice -> peptide path:

```bash
python run.py peptide --input examples/peptide_demo \
  --cds examples/peptide_demo/splice_orfs.tsv \
  --alleles HLA-A*02:01 --mhc-class class1 --out out/peptide_splice_demo
```
