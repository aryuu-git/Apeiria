"""Question catalog loading and deterministic selection."""

import json
from collections.abc import Iterable
from pathlib import Path
from random import Random
from typing import Any

from .models import Difficulty, Question


def default_questions_path() -> Path:
    """Return the bundled development catalog path.

    Returns:
        Path to the canonical Simplified Chinese question catalog.
    """

    return Path(__file__).resolve().parent / "data" / "questions.zh-CN.json"


class QuestionCatalog:
    def __init__(self, questions: Iterable[Question]) -> None:
        self._questions = tuple(questions)
        if not self._questions:
            raise ValueError("question catalog cannot be empty")

    @property
    def size(self) -> int:
        return len(self._questions)

    @property
    def questions(self) -> tuple[Question, ...]:
        return self._questions

    def get(self, subject_id: int) -> Question | None:
        """Return one question by Bangumi subject ID."""

        return next(
            (question for question in self._questions if question.subject_id == subject_id),
            None,
        )

    def choose(
        self,
        *,
        difficulty: Difficulty,
        excluded_subject_ids: set[int],
        random: Random,
    ) -> Question:
        matching = [item for item in self._questions if item.difficulty is difficulty]
        if not matching:
            matching = list(self._questions)
        fresh = [item for item in matching if item.subject_id not in excluded_subject_ids]
        return random.choice(fresh or matching)


def load_questions(path: Path) -> QuestionCatalog:
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("question file must contain a JSON list")

    questions: list[Question] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each question must be an object")
        hints = tuple(item["hints"])
        if len(hints) != 3:
            raise ValueError("each question must contain exactly three hints")
        questions.append(
            Question(
                subject_id=int(item["subject_id"]),
                title=str(item["title"]),
                aliases=tuple(str(alias) for alias in item["aliases"]),
                emoji=str(item["emoji"]),
                difficulty=Difficulty(item["difficulty"]),
                hints=(str(hints[0]), str(hints[1]), str(hints[2])),
                explanation=str(item["explanation"]),
            )
        )
    return QuestionCatalog(questions)
