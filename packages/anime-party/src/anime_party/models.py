"""Immutable game models and answer normalization."""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


_SEPARATOR_PATTERN = re.compile(r"[\W_]+", flags=re.UNICODE)


def normalize_answer(value: str) -> str:
    """Normalize punctuation, width, whitespace, and letter case for matching."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _SEPARATOR_PATTERN.sub("", normalized)


@dataclass(frozen=True, slots=True)
class Question:
    subject_id: int
    title: str
    aliases: tuple[str, ...]
    emoji: str
    difficulty: Difficulty
    hints: tuple[str, str, str]
    explanation: str

    def accepts(self, answer: str) -> bool:
        candidate = normalize_answer(answer)
        return bool(candidate) and candidate in {
            normalize_answer(name) for name in (self.title, *self.aliases)
        }
