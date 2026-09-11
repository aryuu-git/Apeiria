"""User-facing rendering kept outside the deterministic game state machine."""

from random import Random

from .engine import GameReply, ReplyKind
from .models import Difficulty

WRONG_ANSWER_LINES = (
    "还不对。可以继续猜，或者说“提示”。",
    "差一点！再想想，或说“提示”。",
    "不是它哦。继续猜，或者要一个“提示”。",
    "没猜中～换个思路试试，也可以“提示”。",
    "不对哦。需要线索就说“提示”。",
)


class ChineseGamePresenter:
    """Render domain replies in concise Simplified Chinese."""

    def __init__(self, random: Random | None = None) -> None:
        self._random = random

    def render(self, reply: GameReply) -> tuple[str, ...]:
        question = reply.question
        match reply.kind:
            case ReplyKind.IGNORED:
                return ()
            case ReplyKind.QUESTION:
                assert question is not None
                return (f"猜猜这部动画：{question.emoji}",)
            case ReplyKind.DIFFICULTY_CHANGED:
                assert question is not None and reply.difficulty is not None
                label = {
                    Difficulty.EASY: "简单",
                    Difficulty.NORMAL: "普通",
                    Difficulty.HARD: "困难",
                }[reply.difficulty]
                return (f"已切换为{label}难度。", f"猜猜这部动画：{question.emoji}")
            case ReplyKind.PAUSED:
                return ("游戏已暂停。想继续时，对我说“来一个”。",)
            case ReplyKind.NO_ACTIVE_QUESTION:
                return ("现在没有进行中的题目。对我说“来一个”吧。",)
            case ReplyKind.HINT:
                assert reply.hint_level is not None and reply.hint is not None
                return (f"提示 {reply.hint_level}/3：{reply.hint}",)
            case ReplyKind.HINTS_EXHAUSTED:
                return ("三层提示已经全部给出。可以继续猜，或说“公布答案”。",)
            case ReplyKind.REVEALED:
                assert question is not None
                return (f"答案是《{question.title}》。{question.explanation}",)
            case ReplyKind.WRONG_ANSWER:
                line = (
                    self._random.choice(WRONG_ANSWER_LINES)
                    if self._random is not None
                    else WRONG_ANSWER_LINES[0]
                )
                return (line,)
            case ReplyKind.CORRECT_ANSWER:
                assert question is not None
                return (f"答对了，是《{question.title}》！{question.explanation}",)

        raise AssertionError(f"unsupported reply kind: {reply.kind}")
