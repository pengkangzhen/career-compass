"""Career-Compass test suite."""
import os
from pathlib import Path

import pytest

# 示例数据目录（非 gitignore 的 data/examples）
EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture
def examples_env(monkeypatch, examples_dir):
    monkeypatch.setenv("CC_DATA", str(examples_dir))
