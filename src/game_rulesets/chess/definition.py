from game_rulesets.chess.engine import ChessEngine
from game_rulesets.games import GameDefinition

AI_RULES = """Chess is played with player x as White and player o as Black. White moves
first, then turns alternate. Submit legal moves using UCI notation with the JSON payload
{"uci": "e2e4"}. Promotion moves include the promotion piece, such as "e7e8q". The
engine enforces legal chess moves, including check, castling, en passant, promotion,
checkmate, stalemate, insufficient material, and claimable draw rules supported by the
underlying chess rules library. Checkmate is a win for the mating player. Drawn terminal
positions return a draw."""

definition = GameDefinition(
    key=ChessEngine.key,
    engine=ChessEngine(),
    title="Chess",
    summary="Classic chess with UCI moves and full legal move validation.",
    ai_rules=AI_RULES,
)
