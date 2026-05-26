from collections import Counter
from random import Random
from typing import Any, Literal

from pydantic import BaseModel

from game_rulesets.base import (
    PUBLIC_VIEWER,
    ActionSpace,
    GameObservation,
    PlayerId,
    RulesTransition,
    action_to_dict,
    next_player,
    transition,
)
from game_rulesets.battleship.actions import (
    BattleshipFleetSetup,
    BattleshipShipPlacement,
    BattleshipShot,
)
from game_rulesets.battleship.settings import (
    BattleshipRuntimeSettings,
    BattleshipSettings,
    battleship_settings_from_snapshot,
    resolve_battleship_settings,
)
from game_rulesets.enums import GameResult

PLAYER_TO_VIEWER = {"x": "player_1", "o": "player_2"}
VIEWER_TO_PLAYER = {"player_1": "x", "player_2": "o"}


class BattleshipEngine:
    key = "battleship"
    display_name = "Battleship"

    def resolve_settings(self) -> BattleshipRuntimeSettings:
        return resolve_battleship_settings()

    def settings_from_snapshot(self, snapshot: dict) -> BattleshipRuntimeSettings:
        return battleship_settings_from_snapshot(snapshot)

    def initial_state(
        self,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> dict:
        settings = resolve_battleship_settings(settings)
        return {
            "phase": "setup",
            "rows": settings.rows,
            "columns": settings.columns,
            "fleets": {
                "x": {"ships": [], "shots": []},
                "o": {"ships": [], "shots": []},
            },
        }

    def validate_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> BaseModel:
        settings = resolve_battleship_settings(settings)
        if state["phase"] == "setup":
            setup = BattleshipFleetSetup.model_validate(action_to_dict(action))
            _validated_fleet([ship.model_dump() for ship in setup.ships], settings)
            return setup
        shot = BattleshipShot.model_validate(action_to_dict(action))
        _validate_shot(state, shot, player_id, settings)
        return shot

    def legal_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> ActionSpace:
        settings = resolve_battleship_settings(settings)
        if state["phase"] == "setup":
            return ActionSpace(
                player_id=player_id,
                phase="setup",
                actions=(),
                exhaustive=False,
                reason="Fleet setup space is too large to enumerate; use sample_actions.",
            )
        actions = [
            BattleshipShot(row=row, col=col)
            for row in range(settings.rows)
            for col in range(settings.columns)
            if not _already_targeted(state, player_id, row, col)
        ]
        return ActionSpace(
            player_id=player_id,
            phase="battle",
            actions=actions,
            total_count=len(actions),
        )

    def sample_actions(
        self,
        state: dict,
        player_id: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
        *,
        limit: int,
        random: Random | None = None,
    ) -> ActionSpace:
        settings = resolve_battleship_settings(settings)
        if limit < 1:
            raise ValueError("limit must be positive")
        random = random or Random()
        if state["phase"] != "setup":
            actions = list(self.legal_actions(state, player_id, settings).actions)
            return ActionSpace(
                player_id=player_id,
                phase="battle",
                actions=actions[:limit],
                exhaustive=len(actions) <= limit,
                total_count=len(actions),
            )
        return ActionSpace(
            player_id=player_id,
            phase="setup",
            actions=[self._random_setup(settings, random) for _ in range(limit)],
            exhaustive=False,
            reason="Sampled legal fleet setups.",
        )

    def random_action(
        self,
        state: dict,
        player_id: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
        random: Random | None = None,
    ) -> BaseModel:
        settings = resolve_battleship_settings(settings)
        random = random or Random()
        if state["phase"] == "setup":
            return self._random_setup(settings, random)
        actions = list(self.legal_actions(state, player_id, settings).actions)
        if not actions:
            raise ValueError("No legal actions are available")
        return random.choice(actions)

    def apply_action(
        self,
        state: dict,
        action: BaseModel | dict,
        player_id: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> RulesTransition:
        if state["phase"] == "setup":
            setup = BattleshipFleetSetup.model_validate(action_to_dict(action))
            return self.apply_setup(
                state,
                [ship.model_dump() for ship in setup.ships],
                player_id,
                settings,
            )
        return self.apply_shot(state, action, player_id, settings)

    def apply_move(
        self,
        state: dict,
        move: BaseModel | dict,
        player: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> RulesTransition:
        return self.apply_shot(state, move, player, settings)

    def apply_setup(
        self,
        state: dict,
        ships: list[dict],
        player: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_battleship_settings(settings)
        if state["phase"] != "setup":
            raise ValueError("Fleet setup is already complete")
        if state["fleets"][player]["ships"]:
            raise ValueError("Fleet is already submitted")

        fleet = _validated_fleet(ships, settings)
        next_state = _copy_state(state)
        next_state["fleets"][player]["ships"] = fleet
        if not next_state["fleets"][next_player(player)]["ships"]:
            return transition(next_state, next_player(player))
        next_state["phase"] = "battle"
        return transition(next_state, "x")

    def apply_shot(
        self,
        state: dict,
        shot: BaseModel | dict,
        player: PlayerId,
        settings: BattleshipSettings | BattleshipRuntimeSettings | None = None,
    ) -> RulesTransition:
        settings = resolve_battleship_settings(settings)
        shot = BattleshipShot.model_validate(action_to_dict(shot))
        _validate_shot(state, shot, player, settings)

        target = next_player(player)
        next_state = _copy_state(state)
        target_ship = _ship_at(next_state["fleets"][target]["ships"], shot.row, shot.col)
        hit = target_ship is not None
        sunk = False
        if target_ship is not None:
            target_ship["hits"].append({"row": shot.row, "col": shot.col})
            sunk = len(target_ship["hits"]) == target_ship["length"]

        shot_result = {"row": shot.row, "col": shot.col, "hit": hit, "sunk": sunk}
        next_state["fleets"][player]["shots"].append(shot_result)

        if _all_ships_sunk(next_state["fleets"][target]["ships"]):
            return transition(next_state, None, result=GameResult.WIN, winner_player_id=player)
        return transition(next_state, next_player(player))

    def public_state(self, state: dict) -> dict:
        return _visible_state(state, PUBLIC_VIEWER)

    def observations_for_transition(
        self,
        *,
        event_payload: dict,
        state_before: dict | None,
        state_after: dict,
        settings: Any | None = None,
    ) -> dict[PlayerId, GameObservation]:
        return {
            viewer: GameObservation(
                visible_event_payload=_visible_event_payload(event_payload, viewer),
                visible_state_before=(
                    _visible_state(state_before, viewer) if state_before is not None else None
                ),
                visible_state_after=_visible_state(state_after, viewer),
            )
            for viewer in (PUBLIC_VIEWER, "player_1", "player_2")
        }

    def _random_setup(
        self,
        settings: BattleshipRuntimeSettings,
        random: Random,
    ) -> BattleshipFleetSetup:
        ships: list[BattleshipShipPlacement] = []
        occupied: set[tuple[int, int]] = set()
        for length in settings.ship_lengths:
            for _ in range(1000):
                orientation: Literal["horizontal", "vertical"] = random.choice(
                    ["horizontal", "vertical"]
                )
                max_row = settings.rows - (length if orientation == "vertical" else 1)
                max_col = settings.columns - (length if orientation == "horizontal" else 1)
                row = random.randint(0, max_row)
                col = random.randint(0, max_col)
                cells = _ship_cells(row, col, length, orientation)
                if not any(cell in occupied for cell in cells):
                    occupied.update(cells)
                    ships.append(
                        BattleshipShipPlacement(
                            length=length,
                            row=row,
                            col=col,
                            orientation=orientation,
                        )
                    )
                    break
            else:
                raise ValueError("Could not generate legal fleet setup")
        return BattleshipFleetSetup(ships=ships)


def _validate_shot(
    state: dict,
    shot: BattleshipShot,
    player: PlayerId,
    settings: BattleshipRuntimeSettings,
) -> None:
    if state["phase"] != "battle":
        raise ValueError("Both fleets must be submitted before firing")
    if shot.row >= settings.rows or shot.col >= settings.columns:
        raise ValueError("Shot is outside the board")
    if _already_targeted(state, player, shot.row, shot.col):
        raise ValueError("Cell was already targeted")


def _validated_fleet(ships: list[dict], settings: BattleshipRuntimeSettings) -> list[dict]:
    submitted_lengths = Counter(ship.get("length") for ship in ships)
    expected_lengths = Counter(settings.ship_lengths)
    if submitted_lengths != expected_lengths:
        raise ValueError("Fleet must include exactly the configured ship lengths")

    occupied: set[tuple[int, int]] = set()
    fleet = []
    for index, ship in enumerate(ships):
        length = ship["length"]
        row = ship["row"]
        col = ship["col"]
        orientation = ship["orientation"]
        cells = _ship_cells(row, col, length, orientation)
        if any(
            cell_row >= settings.rows or cell_col >= settings.columns
            for cell_row, cell_col in cells
        ):
            raise ValueError("Ship is outside the board")
        if any(cell in occupied for cell in cells):
            raise ValueError("Ships may not overlap")
        occupied.update(cells)
        fleet.append(
            {
                "id": f"{index}",
                "length": length,
                "cells": [{"row": cell_row, "col": cell_col} for cell_row, cell_col in cells],
                "hits": [],
            }
        )
    return fleet


def _ship_cells(row: int, col: int, length: int, orientation: str) -> list[tuple[int, int]]:
    if orientation == "horizontal":
        return [(row, col + offset) for offset in range(length)]
    if orientation == "vertical":
        return [(row + offset, col) for offset in range(length)]
    raise ValueError("Ship orientation must be horizontal or vertical")


def _copy_state(state: dict) -> dict:
    return {
        "phase": state["phase"],
        "rows": state["rows"],
        "columns": state["columns"],
        "fleets": {
            player: {
                "ships": [
                    {
                        "id": ship["id"],
                        "length": ship["length"],
                        "cells": [cell.copy() for cell in ship["cells"]],
                        "hits": [hit.copy() for hit in ship["hits"]],
                    }
                    for ship in fleet["ships"]
                ],
                "shots": [shot.copy() for shot in fleet["shots"]],
            }
            for player, fleet in state["fleets"].items()
        },
    }


def _ship_at(ships: list[dict], row: int, col: int) -> dict | None:
    for ship in ships:
        if any(cell["row"] == row and cell["col"] == col for cell in ship["cells"]):
            return ship
    return None


def _all_ships_sunk(ships: list[dict]) -> bool:
    return bool(ships) and all(len(ship["hits"]) == ship["length"] for ship in ships)


def _already_targeted(state: dict, player: PlayerId, row: int, col: int) -> bool:
    return any(
        existing["row"] == row and existing["col"] == col
        for existing in state["fleets"][player]["shots"]
    )


def _visible_state(state: dict, viewer: PlayerId) -> dict:
    visible = {
        "phase": state["phase"],
        "rows": state["rows"],
        "columns": state["columns"],
        "fleets": {},
    }
    for player, fleet in state["fleets"].items():
        viewer_player = VIEWER_TO_PLAYER.get(viewer)
        visible["fleets"][player] = {
            "ships": _visible_ships(fleet["ships"]) if player == viewer_player else [],
            "shots": [shot.copy() for shot in fleet["shots"]],
            "ship_count": len(fleet["ships"]),
            "unsunk_ship_count": sum(
                1 for ship in fleet["ships"] if len(ship["hits"]) < ship["length"]
            ),
        }
    return visible


def _visible_ships(ships: list[dict]) -> list[dict]:
    return [
        {
            "id": ship["id"],
            "length": ship["length"],
            "cells": [cell.copy() for cell in ship["cells"]],
            "hits": [hit.copy() for hit in ship["hits"]],
        }
        for ship in ships
    ]


def _visible_event_payload(payload: dict, viewer: PlayerId) -> dict:
    if payload.get("action") != "setup":
        return payload
    player = payload.get("player")
    if isinstance(player, str) and PLAYER_TO_VIEWER.get(player) == viewer:
        return payload
    return {
        "action": "setup",
        "player": payload.get("player"),
        "ship_lengths": payload.get("ship_lengths", []),
    }
