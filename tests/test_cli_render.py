import argparse
import shutil
from pathlib import Path

import career_compass.cli as cli
from career_compass.cli import cmd_render_opportunities


def test_render_opportunities_from_draft(examples_dir: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "DATA", tmp_path)
    monkeypatch.setattr(cli, "OPPORTUNITIES_YAML", tmp_path / "opportunities.yaml")
    monkeypatch.setattr(cli, "OPPORTUNITIES_DRAFT", tmp_path / "opportunities.draft.yaml")
    monkeypatch.setattr(cli, "OPPORTUNITIES_MD", tmp_path / "opportunities.md")

    for name in ("profile.yaml", "constraints.yaml", "opportunities.yaml"):
        shutil.copy(examples_dir / name, tmp_path / name)
    draft = tmp_path / "opportunities.draft.yaml"
    shutil.copy(examples_dir / "opportunities.yaml", draft)
    (tmp_path / "opportunities.yaml").unlink()

    code = cmd_render_opportunities(argparse.Namespace())
    assert code == 0
    assert (tmp_path / "opportunities.yaml").is_file()
    assert (tmp_path / "opportunities.md").is_file()
