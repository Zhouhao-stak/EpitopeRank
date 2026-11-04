"""Tests for the rMATS event parser (the only supported input format)."""


import pytest
from pathlib import Path
from splicegaip.splicing.parsers.rmats import parse_rmats_file


class TestRmatsParser:
    """Test cases for rMATS parser."""

    def test_parse_se_events(self, tmp_path):
        """Test parsing SE (Skipped Exon) events from rMATS output."""
        # Create a temporary test file
        test_file = tmp_path / "SE.MATS.JC.txt"
        test_file.write_text(
            "ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\t"
            "upstreamES\tupstreamEE\tdownstreamES\tdownstreamEE\tID\t"
            "IncFormLen\tSkipFormLen\tIJC_SAMPLE_1\tIJC_SAMPLE_2\tSJC_SAMPLE_1\tSJC_SAMPLE_2\tPValue\tFDR\t"
            "IncLevel1\tIncLevel2\tIncLevelDifference\n"
            "1\tENSG00000000001\tTEST_GENE1\tchr1\t+\t1000\t1100\t900\t950\t"
            "1200\t1250\t1\t50\t100\t10,12\t5,6\t3,4\t2,3\t0.01\t0.05\t0.8,0.75\t0.3,0.35\t0.45\n"
        )

        result = parse_rmats_file(
            str(test_file), 
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 1
        event = result[0]
        assert event.gene_id == "ENSG00000000001"
        assert event.gene_symbol == "TEST_GENE1"
        assert event.chromosome == "chr1"
        assert event.event_type == "SE"
        # delta_psi = mean(group2) - mean(group1) = 0.325 - 0.775 = -0.45
        assert event.delta_psi is not None
        assert abs(event.fdr - 0.05) < 0.01

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty rMATS file."""
        test_file = tmp_path / "empty.MATS.JC.txt"
        test_file.write_text("")

        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 0

    def test_parse_invalid_format(self, tmp_path):
        """Test handling of invalid rMATS format."""
        test_file = tmp_path / "invalid.MATS.JC.txt"
        test_file.write_text("invalid content\nno proper columns")

        # Should handle gracefully without crashing
        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )
        assert isinstance(result, list)

    def test_coordinate_extraction(self, tmp_path):
        """Test genomic coordinate extraction."""
        test_file = tmp_path / "SE.MATS.JC.txt"
        test_file.write_text(
            "ID\tGeneID\tgeneSymbol\tchr\tstrand\texonStart_0base\texonEnd\t"
            "upstreamES\tupstreamEE\tdownstreamES\tdownstreamEE\tID\t"
            "IncFormLen\tSkipFormLen\tIJC_SAMPLE_1\tIJC_SAMPLE_2\tSJC_SAMPLE_1\tSJC_SAMPLE_2\tPValue\tFDR\t"
            "IncLevel1\tIncLevel2\tIncLevelDifference\n"
            "1\tENSG00000000001\tTEST_GENE\tchr1\t+\t1000\t1100\t900\t950\t"
            "1200\t1250\t1\t50\t100\t10\t5\t3\t2\t0.01\t0.05\t0.8\t0.3\t0.5\n"
        )

        result = parse_rmats_file(
            str(test_file),
            event_type="SE",
            group1_samples=["sample1"],
            group2_samples=["sample2"]
        )

        assert len(result) == 1
        assert result[0].genomic_coordinates is not None
        assert "chr1" in result[0].genomic_coordinates
