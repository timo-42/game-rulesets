from game_rulesets.games import GameDefinition
from game_rulesets.nine_mens_morris.engine import NineMensMorrisEngine

AI_RULES = """Nine Men's Morris is played on 24 connected points. Players x and o each
place nine pieces, one per turn, on empty points. A legal placement uses
{"action": "place", "position": "a1"}. After all pieces are placed, players move one
piece per turn to an adjacent empty point using {"action": "move", "from_position":
"a1", "to_position": "d1"}. With the standard flying rule enabled, a player reduced to
three pieces may move from any occupied point to any empty point. Whenever a move or
placement forms a new mill, three of the player's pieces on one board line, the action
must include remove_position to capture one opponent piece. Pieces in an opponent mill
cannot be captured while the opponent has any piece outside a mill. A player wins after
placement is complete by reducing the opponent below three pieces or leaving the
opponent with no legal move."""

definition = GameDefinition(
    key=NineMensMorrisEngine.key,
    engine=NineMensMorrisEngine(),
    title="Nine Men's Morris",
    summary="Classic mill-forming game with placement, movement, flying, and captures.",
    ai_rules=AI_RULES,
)
