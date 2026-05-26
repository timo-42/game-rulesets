from dataclasses import dataclass

from game_rulesets.base import RulesEngine


@dataclass(frozen=True)
class GameDefinition:
    key: str
    engine: RulesEngine
    title: str
    summary: str
    ai_rules: str
