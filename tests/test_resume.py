"""Resume upload → profile extraction tests.

Covers the pure-Python parts (text extraction + field-level merge) without
hitting any LLM. LLM-dependent paths are guarded by ``_call_llm_for_extraction``
and tested indirectly via stubs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from career_compass.intake.resume import (
    MAX_RESUME_BYTES,
    ResumeError,
    ResumeExtractResult,
    extract_profile_from_resume,
    extract_text,
    merge_profile,
)


# ---------------------------------------------------------------------------
# extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_txt_utf8(self):
        text = extract_text("resume.txt", "张三 / Python 工程师".encode("utf-8"))
        assert "张三" in text
        assert "Python 工程师" in text

    def test_md_markdown_alias(self):
        for name in ("cv.md", "cv.markdown", "cv.text"):
            text = extract_text(name, b"hello world")
            assert "hello world" in text

    def test_gbk_fallback(self):
        # 简体中文 Windows 简历常用 GBK
        text = extract_text("resume.txt", "李四".encode("gbk"))
        assert "李四" in text

    def test_pdf_extracts_text(self):
        # 用 reportlab 生成一个最简 PDF（如果没装就 skip）
        pytest.importorskip("reportlab")
        from io import BytesIO
        from reportlab.pdfgen import canvas
        buf = BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "John Doe - Data Engineer")
        c.save()
        text = extract_text("resume.pdf", buf.getvalue())
        assert "John Doe" in text

    def test_pdf_scanned_image_returns_error(self):
        pytest.importorskip("reportlab")
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        # 空白页：没有文字
        c.showPage()
        c.save()
        with pytest.raises(ResumeError, match="未抽取到任何文本"):
            extract_text("blank.pdf", buf.getvalue())

    def test_unsupported_extension(self):
        with pytest.raises(ResumeError, match="不支持的文件类型"):
            extract_text("resume.docx", b"anything")

    def test_invalid_pdf(self):
        with pytest.raises(ResumeError, match="PDF 解析失败"):
            extract_text("fake.pdf", b"not really a pdf")


# ---------------------------------------------------------------------------
# merge_profile
# ---------------------------------------------------------------------------

class TestMergeProfile:
    def test_fills_empty_scalar(self):
        existing = {"current_role": None}
        extracted = {"current_role": "数据工程师"}
        merged, filled, skipped = merge_profile(existing, extracted)
        assert merged["current_role"] == "数据工程师"
        assert filled == ["current_role"]
        assert skipped == []

    def test_skips_non_empty_scalar(self):
        """已有 current_role 不应被覆盖。"""
        existing = {"current_role": "手动填的角色"}
        extracted = {"current_role": "简历里的角色"}
        merged, filled, skipped = merge_profile(existing, extracted)
        assert merged["current_role"] == "手动填的角色"
        assert filled == []
        assert skipped == ["current_role"]

    def test_fills_empty_lists(self):
        existing: dict[str, Any] = {}
        extracted = {
            "education": [{"level": "bachelor", "school": "清华", "major": "CS"}],
            "experience": [{"company": "Acme", "role": "Eng", "period": "2020-2024", "scope": "x"}],
            "strength_evidence": [{"claim": "擅长 X", "proof": "100w 用户"}],
        }
        merged, filled, _ = merge_profile(existing, extracted)
        assert len(merged["education"]) == 1
        assert len(merged["experience"]) == 1
        assert len(merged["strength_evidence"]) == 1
        assert set(filled) == {"education", "experience", "strength_evidence"}

    def test_skips_non_empty_lists(self):
        existing = {"experience": [{"company": "X", "role": "Y", "period": "1", "scope": "s"}]}
        extracted = {"experience": [{"company": "Y", "role": "Z", "period": "2", "scope": "t"}]}
        merged, filled, skipped = merge_profile(existing, extracted)
        assert len(merged["experience"]) == 1
        assert merged["experience"][0]["company"] == "X"
        assert "experience" in skipped
        assert filled == []

    def test_skills_merge_per_tier(self):
        existing = {"skills": {"core": ["Python"], "adjacent": [], "frontier": []}}
        extracted = {"skills": {"core": ["Java"], "adjacent": ["Rust"], "frontier": []}}
        merged, filled, skipped = merge_profile(existing, extracted)
        # core 已有不覆盖
        assert merged["skills"]["core"] == ["Python"]
        assert "skills.core" in skipped
        # adjacent 空可填
        assert merged["skills"]["adjacent"] == ["Rust"]
        assert "skills.adjacent" in filled

    def test_skills_initialized_when_absent(self):
        existing: dict[str, Any] = {}
        extracted = {"skills": {"core": ["Python"]}}
        merged, filled, _ = merge_profile(existing, extracted)
        assert merged["skills"]["core"] == ["Python"]
        assert "skills.core" in filled

    def test_empty_extraction_is_noop(self):
        existing = {"current_role": "Engineer"}
        merged, filled, skipped = merge_profile(existing, {})
        assert merged == {"current_role": "Engineer"}
        assert filled == []
        assert skipped == []

    def test_filters_garbage_entries(self):
        """空 dict / 空字符串不应进列表。"""
        extracted = {
            "education": [{}, None],  # type: ignore
            "skills": {"core": ["", "  ", "Python"]},
        }
        merged, filled, _ = merge_profile({}, extracted)
        # education 全空 → 不写入
        assert "education" not in merged or merged.get("education") == []
        # core 已过滤空字符串
        if "skills.core" in filled:
            assert merged["skills"]["core"] == ["Python"]


# ---------------------------------------------------------------------------
# extract_profile_from_resume (top-level, with stubbed LLM)
# ---------------------------------------------------------------------------

class _StubLLM:
    """Replays a canned JSON payload; ignores inputs."""

    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        import json
        return f"```json\n{json.dumps(self._payload, ensure_ascii=False)}\n```"


RESUME_SAMPLE = (
    "张三，5 年数据工程师经验，主要用 Python / SQL 构建数据管道。"
    "本科清华计算机，硕士北大统计学。曾在 Acme 带队把 ETL 时延从 12h 降到 2h。"
).encode("utf-8")


class TestExtractProfileFromResume:
    def test_writes_merged_profile_yaml(self, tmp_path: Path):
        # 起点：空 profile
        (tmp_path / "profile.yaml").write_text(
            "name: null\ncurrent_role: null\neducation: []\nskills:\n  core: []\n  adjacent: []\n  frontier: []\n",
            encoding="utf-8",
        )
        stub = _StubLLM({
            "extracted_profile": {
                "current_role": "数据工程师",
                "education": [{"level": "master", "school": "北大", "major": "统计学"}],
                "skills": {"core": ["Python", "SQL"]},
            },
            "notes": "1 段教育 + 2 个核心技能",
        })

        result = extract_profile_from_resume(
            data_dir=tmp_path,
            filename="cv.txt",
            content=RESUME_SAMPLE,
            llm=stub,  # type: ignore
        )

        assert result.ok is True
        assert "current_role" in result.merged_keys
        assert "education" in result.merged_keys
        assert "skills.core" in result.merged_keys
        assert result.files_updated == ["profile.yaml"]

        written = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))
        assert written["current_role"] == "数据工程师"
        assert written["education"][0]["school"] == "北大"
        assert written["skills"]["core"] == ["Python", "SQL"]

    def test_does_not_overwrite_existing(self, tmp_path: Path):
        (tmp_path / "profile.yaml").write_text(
            yaml.safe_dump({
                "current_role": "我手动写的",
                "education": [{"level": "bachelor", "school": "复旦", "major": "CS"}],
                "skills": {"core": ["Rust"], "adjacent": [], "frontier": []},
            }, allow_unicode=True),
            encoding="utf-8",
        )
        stub = _StubLLM({
            "extracted_profile": {
                "current_role": "简历里的角色",
                "education": [{"level": "master", "school": "斯坦福", "major": "MBA"}],
                "skills": {"core": ["Python"]},
            },
            "notes": "",
        })

        result = extract_profile_from_resume(
            data_dir=tmp_path,
            filename="cv.txt",
            content=RESUME_SAMPLE,
            llm=stub,  # type: ignore
        )

        # 简历字段全部被跳过；但 result.ok 仍是 True（解析成功了，只是没新内容）
        assert result.ok is True
        assert result.merged_keys == []
        assert set(result.skipped_keys) == {"current_role", "education", "skills.core"}
        assert result.files_updated == []

        written = yaml.safe_load((tmp_path / "profile.yaml").read_text(encoding="utf-8"))
        assert written["current_role"] == "我手动写的"
        assert written["education"][0]["school"] == "复旦"

    def test_oversize_file_rejected(self, tmp_path: Path):
        result = extract_profile_from_resume(
            data_dir=tmp_path,
            filename="huge.txt",
            content=b"x" * (MAX_RESUME_BYTES + 1),
            llm=_StubLLM({}),  # type: ignore
        )
        assert result.ok is False
        assert "文件过大" in result.error

    def test_unsupported_extension(self, tmp_path: Path):
        result = extract_profile_from_resume(
            data_dir=tmp_path,
            filename="resume.docx",
            content=b"stuff",
            llm=_StubLLM({}),  # type: ignore
        )
        assert result.ok is False
        assert "不支持的文件类型" in result.error

    def test_too_short_text(self, tmp_path: Path):
        result = extract_profile_from_resume(
            data_dir=tmp_path,
            filename="resume.txt",
            content=b"hi",  # 2 字符
            llm=_StubLLM({}),  # type: ignore
        )
        assert result.ok is False
        assert "过短" in result.error
