from game_rulesets.connect_four.engine import ConnectFourEngine
from game_rulesets.games import GameDefinition

AI_RULES = """Connect Four is played on a vertical grid, normally 6 rows by 7 columns.
Two players alternate turns. Player x moves first, then player o, and only the current
turn player may submit a move. A legal move chooses one non-full column using the JSON
payload {"column": <zero-based column>}. The column must be inside the persisted game
settings for the match. The placed disc falls to the lowest empty row in that column.
After each accepted move, the game checks for the configured win length, normally four,
in any horizontal, vertical, or diagonal line connected to the placed disc. If the board
becomes full without a winner, the game is a draw."""

definition = GameDefinition(
    key=ConnectFourEngine.key,
    engine=ConnectFourEngine(),
    title="Connect Four",
    summary="A gravity-based alignment game where agents drop discs to connect a line.",
    ai_rules=AI_RULES,
)
