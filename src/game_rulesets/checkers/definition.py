from game_rulesets.checkers.engine import CheckersEngine
from game_rulesets.games import GameDefinition

AI_RULES = """Checkers is played on the dark squares of an 8 by 8 board. Player x is
the dark side and moves first from the top of the board toward increasing row numbers;
player o moves upward. Submit moves as a path of zero-based squares, for example
{"path": [{"row": 2, "col": 1}, {"row": 3, "col": 0}]} for a simple move or a longer
path for a multi-jump capture. Men move one diagonal step forward and capture by jumping
forward over an adjacent opposing piece into the empty square beyond. Captures are
mandatory by default. Kings move and capture one diagonal step in any direction. A man
is crowned when it reaches the farthest row, ending that move. A player wins when the
opponent has no pieces or no legal move."""

definition = GameDefinition(
    key=CheckersEngine.key,
    engine=CheckersEngine(),
    title="Checkers",
    summary="American checkers with mandatory captures, kings, promotion, and multi-jumps.",
    ai_rules=AI_RULES,
)
