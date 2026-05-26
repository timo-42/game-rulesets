from game_rulesets.axelrod_tournament.engine import AxelrodTournamentEngine
from game_rulesets.games import GameDefinition

AI_RULES = """Axelrod Tournament is a two-player iterated Prisoner's Dilemma match using
the classic Axelrod parameters: 200 rounds and the per-round payoffs temptation 5,
mutual cooperation 3, mutual defection 1, and sucker 0. Each round, player x submits a
hidden choice first and player o submits second. A legal move uses the JSON payload
{"choice": "cooperate"} or {"choice": "defect"}. After both choices are submitted, the
round is scored: cooperate/cooperate gives both players 3 points, defect/defect gives
both players 1 point, defect against cooperate gives the defector 5 points and the
cooperator 0 points. After the configured final round, the higher total score wins; an
equal total score is a draw."""

definition = GameDefinition(
    key=AxelrodTournamentEngine.key,
    engine=AxelrodTournamentEngine(),
    title="Axelrod Tournament",
    summary="A classic 200-round iterated Prisoner's Dilemma match.",
    ai_rules=AI_RULES,
)
