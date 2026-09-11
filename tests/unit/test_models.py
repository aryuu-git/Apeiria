from anime_party.models import Difficulty, Question, normalize_answer


def test_normalize_answer_ignores_width_case_spaces_and_punctuation() -> None:
    assert normalize_answer("ＳＴＥＩＮＳ；ＧＡＴＥ") == normalize_answer("steins gate")


def test_question_accepts_alias() -> None:
    question = Question(
        subject_id=1,
        title="命运石之门",
        aliases=("Steins;Gate", "石头门"),
        emoji="⌚🍌📱",
        difficulty=Difficulty.NORMAL,
        hints=("时间", "秋叶原", "电话微波炉"),
        explanation="测试说明。",
    )

    assert question.accepts("STEINS GATE")
    assert question.accepts("石头门")
    assert not question.accepts("命运之夜")
