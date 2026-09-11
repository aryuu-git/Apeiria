"""Unit tests for the persona asset loader."""

from pathlib import Path

from apeiria_core import build_persona_prompt


def _make_skill(directory: Path) -> None:
    (directory / "SKILL.md").write_text(
        """---
name: apeiria-roleplay
description: test skill
---

# 艾佩理雅角色扮演

## 恒常人格

- 纯真、善良、认真、好奇。

## 按需读取

- 这一节属于会话流程，运行时不需要。

## 回应流程

1. 这一节也不需要。
""",
        encoding="utf-8",
    )


def test_builds_prompt_and_trims_session_sections(tmp_path: Path) -> None:
    references = tmp_path / "references"
    references.mkdir()
    _make_skill(tmp_path)
    (references / "voice.md").write_text(
        "# 语言与对白指南\n\n- 自称艾佩理雅，称呼用户为 Owner。\n",
        encoding="utf-8",
    )

    prompt = build_persona_prompt(tmp_path)

    assert prompt is not None
    assert "纯真、善良、认真、好奇" in prompt
    assert "自称艾佩理雅" in prompt
    assert "按需读取" not in prompt
    assert "回应流程" not in prompt
    assert "name: apeiria-roleplay" not in prompt  # frontmatter trimmed


def test_missing_directory_returns_none(tmp_path: Path) -> None:
    assert build_persona_prompt(tmp_path / "absent") is None
    assert build_persona_prompt(None) is None


def test_directory_without_skill_returns_none(tmp_path: Path) -> None:
    (tmp_path / "references").mkdir()
    assert build_persona_prompt(tmp_path) is None
