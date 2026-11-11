"""输入目录诊断：误选多数据集上级目录时必须给明确提示，不再静默产出空报告。"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from epitoperank.data.loader import load_dataset

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "demo_rmats"


def _dataset_copy(target: Path) -> None:
    assert EXAMPLE.is_dir(), "examples/demo_rmats is required for this test"
    shutil.copytree(EXAMPLE, target)


def test_single_nested_dataset_uses_its_sample_metadata(tmp_path: Path) -> None:
    """根目录只包一个数据集时，自动读取子目录样本表并写诊断。"""
    root = tmp_path / "mixed_root"
    root.mkdir()
    _dataset_copy(root / "dataset_A")

    dataset = load_dataset(root)
    assert dataset.samples, "样本表应从子目录读取"
    assert dataset.groups, "应还原出分组信息"
    assert any("已自动从" in item for item in dataset.diagnostics)
    assert "diagnostics" in dataset.summary()
    assert sum(1 for event in dataset.events if event.valid_sample_count) > 0, "有效样本数不应再全为 0"


def test_multiple_nested_datasets_are_rejected_with_guidance(tmp_path: Path) -> None:
    """多个数据集混在一个根目录时明确拒绝，并推荐层级最浅的目录。"""
    root = tmp_path / "mixed_root"
    root.mkdir()
    _dataset_copy(root / "dataset_A")
    _dataset_copy(root / "nested" / "dataset_B")

    with pytest.raises(ValueError) as error:
        load_dataset(root)
    message = str(error.value)
    assert "各自带样本表的数据集" in message
    assert "推荐路径最浅的" in message
    assert "dataset_A" in message


def test_plain_dataset_directory_has_no_diagnostics(tmp_path: Path) -> None:
    """直接指向数据集目录是推荐用法，不应产生告警。"""
    target = tmp_path / "dataset_A"
    _dataset_copy(target)
    dataset = load_dataset(target)
    assert dataset.diagnostics == []
