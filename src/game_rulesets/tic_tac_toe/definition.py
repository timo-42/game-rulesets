from game_rulesets.games import GameDefinition
from game_rulesets.tic_tac_toe.engine import TicTacToeEngine

AI_RULES = """Tic-tac-toe is played on a rectangular grid, normally 3 rows by 3 columns.
Two players alternate turns. Player x moves first, then player o, and only the current
turn player may submit a move. A legal move chooses one empty board cell using the JSON
payload {"row": <zero-based row>, "col": <zero-based column>}. Rows and columns must be
inside the persisted game settings for the match, and occupied cells cannot be reused.
After each accepted move, the mark is placed in that cell. A player wins by occupying
every cell in any complete row, any complete column, or either diagonal when the board is
square. If the board becomes full without a winner, the game is a draw."""

definition = GameDefinition(
    key=TicTacToeEngine.key,
    engine=TicTacToeEngine(),
    title="Tic-tac-toe",
    summary="A two-player grid game where agents race to complete a row, column, or diagonal.",
    ai_rules=AI_RULES,
)
