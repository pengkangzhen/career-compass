"""项目扫描器 —— L0 构建画像辅助：opt-in、范围受限地从代码库提取画像证据。

只遍历用户**点名**的目录，提取**结构化元数据**（语言分布、关键依赖、规模、成果信号、
推断的技能标签），不读取/存储源码内容。输出 safe to inspect / commit。

隐私：永不扫描整盘；只看用户指定路径；不存文件内容，只存计数、声明的依赖名、
从 README/pyproject 取的短描述。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional

from .schema import ProjectEvidence, Scale

# 遍历时跳过的目录（垃圾 / 依赖 / 缓存）
_SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".idea", ".vscode", "dist", "build", ".next", "target", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".codegraph", ".remember", "archive",
    "site-packages", ".cache",
}

# 扩展名 -> 语言
_EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".c": "C", ".h": "C/C++",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".r": "R", ".m": "MATLAB", ".jl": "Julia",
    ".sh": "Shell", ".bash": "Shell",
    ".sql": "SQL",
    ".tex": "LaTeX", ".bib": "BibTeX",
}

# 命中信号表：依赖名(lower) -> 技能标签
_SIGNAL_MAP = {
    "gurobipy": "OR solver (Gurobi)",
    "cplex": "OR solver (CPLEX)",
    "pulp": "OR modeling (PuLP)",
    "ortools": "OR solver (OR-Tools)",
    "pyomo": "OR modeling (Pyomo)",
    "scipy": "scientific computing (SciPy)",
    "langgraph": "LLM multi-agent (LangGraph)",
    "langchain": "LLM framework (LangChain)",
    "autogen": "LLM multi-agent (AutoGen)",
    "crewai": "LLM multi-agent (CrewAI)",
    "llama-index": "LLM framework (LlamaIndex)",
    "openai": "LLM application (OpenAI)",
    "anthropic": "LLM application (Anthropic)",
    "transformers": "ML (Transformers)",
    "torch": "ML (PyTorch)",
    "tensorflow": "ML (TensorFlow)",
    "jax": "ML (JAX)",
    "scikit-learn": "ML (scikit-learn)",
    "numpy": "data (NumPy)",
    "pandas": "data (Pandas)",
    "polars": "data (Polars)",
    "fastapi": "web backend (FastAPI)",
    "flask": "web backend (Flask)",
    "django": "web backend (Django)",
    "react": "frontend (React)",
    "vue": "frontend (Vue)",
    "next": "frontend (Next.js)",
    "playwright": "automation (Playwright)",
    "selenium": "automation (Selenium)",
    "docker": "containerization (Docker)",
    "matplotlib": "viz (matplotlib)",
    "plotly": "viz (Plotly)",
}


def _walk_files(root: Path):
    """遍历文件，跳过垃圾目录。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            yield Path(dirpath) / fn


def _count_languages(root: Path) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for f in _walk_files(root):
        lang = _EXT_LANG.get(f.suffix.lower())
        if lang:
            counter[lang] += 1
    return dict(counter.most_common(8))


def _read_deps(root: Path) -> list[str]:
    """从包文件提取声明的依赖名（规范化为小写、去版本号）。"""
    raw: list[str] = []
    pp = root / "pyproject.toml"
    if pp.exists():
        try:
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
            proj = data.get("project", {})
            raw += proj.get("dependencies", [])
            for opt in proj.get("optional-dependencies", {}).values():
                raw += opt
        except Exception:
            pass
    for req in ("requirements.txt", "requirements.in"):
        rf = root / req
        if rf.exists():
            for line in rf.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith("-"):
                    raw.append(line)
    pj = root / "package.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            for k in ("dependencies", "devDependencies"):
                raw += list((data.get(k) or {}).keys())
        except Exception:
            pass
    # 规范化：去版本/extra，小写，去重保序
    cleaned: list[str] = []
    for d in raw:
        name = re.split(r"[\s<>=!\[~;@]", d.strip(), 1)[0].lower()
        if name and name not in cleaned:
            cleaned.append(name)
    return cleaned


def _key_dependencies(deps: list[str]) -> list[str]:
    return [d for d in deps if d in _SIGNAL_MAP]


def _inferred_signals(deps: list[str]) -> list[str]:
    signals: list[str] = []
    for sig, label in _SIGNAL_MAP.items():
        if sig in deps and label not in signals:
            signals.append(label)
    return signals


_BOILERPLATE = (
    "provides guidance to claude code",
    "when working with code in this repository",
    "this file provides",
)


def _first_prose_line(text: str) -> str:
    """跳过标题/列表项/图片/html/引用/表格/样板话，返回第一段实质散文句。"""
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith(("#", "!", "<", "[", ">", "-", "*", "|", "`")):
            continue
        if any(b in s.lower() for b in _BOILERPLATE):
            continue
        return s[:200]
    return ""


def _description(root: Path) -> str:
    # 1. pyproject description（最干净）
    pp = root / "pyproject.toml"
    if pp.exists():
        try:
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
            desc = (data.get("project", {}) or {}).get("description", "")
            if desc and "add your description" not in desc.lower():
                return desc.strip()
        except Exception:
            pass
    # 2. CLAUDE.md / AGENTS.md 的项目概述（很多项目把一句话定位写这里）
    for cn in ("CLAUDE.md", "AGENTS.md"):
        cf = root / cn
        if cf.exists():
            line = _first_prose_line(cf.read_text(encoding="utf-8", errors="ignore"))
            if line:
                return line
    # 3. README 第一段实质散文
    for rn in ("README.md", "README.rst", "README.txt", "README"):
        rf = root / rn
        if rf.exists():
            line = _first_prose_line(rf.read_text(encoding="utf-8", errors="ignore"))
            if line:
                return line
    return ""
    return ""


def _scale_artifacts_git(root: Path) -> tuple[Scale, list[str], bool, Optional[date]]:
    files = 0
    tex = 0
    has_tests = False
    for f in _walk_files(root):
        files += 1
        suf = f.suffix.lower()
        if suf == ".tex":
            tex += 1
        if not has_tests and ("test" in f.name.lower() or "tests" in f.parent.name.lower()):
            has_tests = True
    artifacts: list[str] = []
    for d in ("paper", "papers", "docs", "doc", "results", "experiments", "benchmarks", "dataset", "datasets"):
        if (root / d).is_dir():
            artifacts.append(f"{d}/")
    if tex:
        artifacts.append(f"LaTeX ({tex} .tex)")

    is_git = (root / ".git").exists()
    commits: Optional[int] = None
    last_commit: Optional[date] = None
    if is_git:
        try:
            r = subprocess.run(
                ["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip().isdigit():
                commits = int(r.stdout.strip())
            r2 = subprocess.run(
                ["git", "-C", str(root), "log", "-1", "--format=%cs"],
                capture_output=True, text=True, timeout=10,
            )
            if r2.returncode == 0 and r2.stdout.strip():
                last_commit = date.fromisoformat(r2.stdout.strip())
        except Exception:
            pass
    return Scale(files=files, commits=commits, has_tests=has_tests), artifacts, is_git, last_commit


def scan_project(path: Path) -> ProjectEvidence:
    """扫描单个项目目录，返回结构化证据。"""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"不是目录: {root}")
    deps = _read_deps(root)
    scale, artifacts, is_git, last_commit = _scale_artifacts_git(root)
    return ProjectEvidence(
        path=str(root),
        name=root.name,
        description=_description(root),
        is_git=is_git,
        last_commit=last_commit,
        languages=_count_languages(root),
        dependency_count=len(deps),
        key_dependencies=_key_dependencies(deps),
        scale=scale,
        artifacts=artifacts,
        inferred_signals=_inferred_signals(deps),
    )
