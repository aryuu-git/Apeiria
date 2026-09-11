"""Assemble the Apeiria roleplay persona assets into a system prompt.

The Owner maintains a persona skill directory (SKILL.md plus reference
sheets). This loader trims the parts that address a conversational
assistant session flow (mode switching, on-demand reading, response
checklist) and keeps the personality, voice, identity, cognition, and
scene-strategy content the runtime LLM needs. Missing directories or
files degrade to ``None`` so callers can fall back to built-in prompts.
"""

from pathlib import Path

SKILL_FILE = "SKILL.md"
REFERENCE_FILES = ("identity.md", "voice.md", "cognition.md", "scenes.md")
SKIPPED_SECTIONS = ("运行模式", "按需读取", "回应流程")


def build_persona_prompt(persona_dir: Path | None) -> str | None:
    """Assemble persona assets into one prompt, or ``None`` when absent."""
    if persona_dir is None or not persona_dir.is_dir():
        return None
    skill_path = persona_dir / SKILL_FILE
    if not skill_path.is_file():
        return None
    sections: list[str] = []
    skill = _load_trimmed_skill(skill_path)
    if skill:
        sections.append(skill)
    for name in REFERENCE_FILES:
        path = persona_dir / "references" / name
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8").strip()
        if body:
            sections.append(f"<!-- 来源：references/{name} -->\n\n{body}")
    return "\n\n".join(sections) or None


def _load_trimmed_skill(path: Path) -> str:
    """Read SKILL.md without frontmatter and assistant-session sections."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :]
    kept: list[str] = []
    skipping = False
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            skipping = any(title == item or title.startswith(item) for item in SKIPPED_SECTIONS)
        if not skipping and line.strip():
            kept.append(line)
    return "\n".join(kept).strip()
