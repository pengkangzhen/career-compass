"""Intake 实时画像预览与进度计算。"""
from __future__ import annotations

from pathlib import Path

from ..pipeline import run_validation
from ..schema import ValidationError, is_placeholder, load_profile
from .gaps import compute_intake_progress, narrative_sections_ok, suggest_followups


def build_intake_status(data_dir: Path) -> dict:
    """供 GUI chat_state / chat_send 使用的完整 intake 状态。"""
    profile_path = data_dir / "profile.yaml"
    narrative_path = data_dir / "narrative.md"

    errors, warnings = run_validation(data_dir)
    extra_gaps: list[str] = []
    preview: dict = {
        "name": None,
        "current_role": None,
        "education": [],
        "core_skills": [],
        "values": [],
        "evidence_count": 0,
        "has_narrative": False,
    }

    name_ok = role_ok = education_ok = skills_ok = evidence_ok = values_ok = False
    narrative_ok = False

    if profile_path.is_file():
        try:
            profile = load_profile(profile_path)
            extra_gaps = profile.gaps()

            if profile.name and not is_placeholder(profile.name):
                preview["name"] = profile.name
                name_ok = True
            if profile.current_role and not is_placeholder(profile.current_role):
                preview["current_role"] = profile.current_role
                role_ok = True

            for edu in profile.sorted_education():
                if not is_placeholder(edu.school) and not is_placeholder(edu.major):
                    preview["education"].append(
                        f"{edu.level_label()} · {edu.school} · {edu.major}"
                    )
            education_ok = bool(preview["education"]) and not any(
                "education" in g for g in extra_gaps
            )

            preview["core_skills"] = [
                s for s in profile.skills.core if not is_placeholder(s)
            ][:6]
            skills_ok = bool(preview["core_skills"]) and not any(
                "skills.core" in g for g in extra_gaps
            )

            preview["evidence_count"] = sum(
                1
                for ev in profile.strength_evidence
                if not is_placeholder(ev.claim) and not is_placeholder(ev.proof)
            )
            evidence_ok = preview["evidence_count"] > 0 and not any(
                "strength_evidence" in g for g in extra_gaps
            )

            preview["values"] = [
                v for v in profile.preferences.values_ranked if not is_placeholder(v)
            ][:5]
            values_ok = bool(preview["values"]) and not any(
                "values_ranked" in g for g in extra_gaps
            )
        except ValidationError:
            pass

        except ValidationError:
            pass

    if narrative_path.is_file():
        text = narrative_path.read_text(encoding="utf-8")
        preview["has_narrative"] = narrative_sections_ok(text)
        narrative_ok = preview["has_narrative"] and not any(
            "narrative" in e.lower() for e in errors
        )

    progress = compute_intake_progress(
        has_profile=profile_path.is_file(),
        name_ok=name_ok,
        role_ok=role_ok,
        education_ok=education_ok,
        skills_ok=skills_ok,
        evidence_ok=evidence_ok,
        values_ok=values_ok,
        narrative_ok=narrative_ok,
    )

    intake_complete = not errors
    if intake_complete:
        progress = compute_intake_progress(
            has_profile=True,
            name_ok=True,
            role_ok=True,
            education_ok=True,
            skills_ok=True,
            evidence_ok=True,
            values_ok=True,
            narrative_ok=True,
        )

    return {
        "profile_preview": preview,
        "progress": progress.to_dict(),
        "gap_hints": [] if intake_complete else suggest_followups(errors, extra_gaps),
        "intake_complete": intake_complete,
        "validation": {"errors": errors, "warnings": warnings},
    }
