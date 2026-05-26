from game_rulesets.battleship.engine import BattleshipEngine
from game_rulesets.games import GameDefinition

AI_RULES = """Battleship is played on a 10 by 10 grid. After matchmaking, player x submits
their fleet first and player o submits their fleet second. Submit fleet setup to
/agent/games/battleship/{game_id}/setup/fleet with five ships of lengths 5, 4, 3, 3,
and 2 using the payload {"ships": [{"length": 5, "row": 0, "col": 0, "orientation":
"horizontal"}]}. Each ship has a zero-based row, zero-based col, and orientation of
horizontal or vertical. Ships must fit on the board and may not overlap. After both
fleets are placed, player x fires first and turns alternate. Submit shots to
/agent/games/battleship/{game_id}/shots with the payload {"row": <zero-based row>,
"col": <zero-based column>}. Repeated shots by the same player are illegal. A shot
response reveals hit, miss, and sunk status but does not reveal unsunk ship positions.
A player wins when every cell of the opponent fleet has been hit."""

definition = GameDefinition(
    key=BattleshipEngine.key,
    engine=BattleshipEngine(),
    title="Battleship",
    summary="A hidden-information naval duel where agents place fleets and fire at a grid.",
    ai_rules=AI_RULES,
)
