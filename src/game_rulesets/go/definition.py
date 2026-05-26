from game_rulesets.games import GameDefinition
from game_rulesets.go.engine import GoEngine

AI_RULES = """Go is played on a square grid, normally 19 by 19. Player x plays black
and moves first; player o plays white and receives komi. Submit moves with
{"move": "play", "row": <zero-based row>, "col": <zero-based column>} or pass with
{"move": "pass"}. Stones are placed on empty intersections. Orthogonally connected
groups with no liberties are captured and removed. Suicide moves are illegal unless
the move captures opposing stones and thereby leaves the played stone with liberties.
The engine enforces simple ko by rejecting a move that recreates the board position
from immediately before the previous move. Two consecutive passes end the game. The
winner is determined by area scoring: stones plus surrounded empty territory, with
komi added to white."""

definition = GameDefinition(
    key=GoEngine.key,
    engine=GoEngine(),
    title="Go",
    summary="Classic Go with captures, suicide rejection, simple ko, passing, and area scoring.",
    ai_rules=AI_RULES,
)
