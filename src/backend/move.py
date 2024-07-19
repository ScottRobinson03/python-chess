from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.piece import Piece
from src.typings import CheckmatesEnemy, ChecksEnemy, ColumnIndex, RawMove, RowIndex


@dataclass(repr=False, eq=False)
class MoveComponent:
    before: Piece
    after: Piece
    captured_piece: Piece | None
    checks_enemy: bool
    checkmates_enemy: bool

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MoveComponent):
            other = other.__repr__()
        if isinstance(other, str):
            return self.__repr__() == other
        raise TypeError(
            f"Unable to compare equality between type {type(self).__name__!r} and {type(other).__name__!r}."
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, MoveComponent):
            return self.__repr__() < other.__repr__()
        raise TypeError(f"Unable to compare between type {type(self).__name__!r} and {type(other).__name__!r}.")

    def __repr__(self) -> str:
        capture_str = "x" if self.captured_piece is not None else ""
        pawn_promotion_str = self.after.name if self.after.name != self.before.name else ""
        check_str = "#" if self.checkmates_enemy else "+" if self.checks_enemy else ""
        return f"{self.before.algebraic_position}{capture_str}{self.after.position}{pawn_promotion_str}{check_str}"


@dataclass(eq=False)
class Move:
    components: list[MoveComponent]

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            other = [other]

        if isinstance(other, list):
            actual_moves = sorted(map(repr, self.components))
            return actual_moves == sorted(other)

        raise TypeError(
            f"Unable to compare equality between type {type(self).__name__!r} and {type(other).__name__!r}."
        )

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Move):
            return self.components < other.components
        raise TypeError(f"Unable to compare between type {type(self).__name__!r} and {type(other).__name__!r}.")

    def ends_at(self, col_indx: ColumnIndex, row_indx: RowIndex) -> bool:
        return any(
            move_component.after.col_indx == col_indx and move_component.after.row_indx == row_indx
            for move_component in self.components
        )

    def starts_at(self, col_indx: ColumnIndex, row_indx: RowIndex) -> bool:
        return any(
            move_component.before.col_indx == col_indx and move_component.before.row_indx == row_indx
            for move_component in self.components
        )

    @classmethod
    def from_raw_moves(cls, raw_moves: list[tuple[RawMove, ChecksEnemy, CheckmatesEnemy]]) -> Move:
        return cls(
            [
                *map(
                    lambda raw_move: MoveComponent(
                        raw_move[0][0], raw_move[0][1], raw_move[0][2], raw_move[1], raw_move[2]
                    ),
                    raw_moves,
                )
            ]
        )

    def to_raw_moves(self) -> list[RawMove]:
        return [
            (move_component.before, move_component.after, move_component.captured_piece)
            for move_component in self.components
        ]

    @property
    def captured_piece(self) -> Piece | None:
        return next(
            (move_component.captured_piece for move_component in self.components if move_component.captured_piece), None
        )

    @property
    def captures_piece(self) -> bool:
        return self.captured_piece is not None

    @property
    def checks_enemy(self) -> bool:
        return any(move_component.checks_enemy for move_component in self.components)

    @property
    def checkmates_enemy(self) -> bool:
        return any(move_component.checkmates_enemy for move_component in self.components)

    @property
    def en_passant_square(self) -> tuple[ColumnIndex, RowIndex] | None:
        if (
            len(self.components) == 1
            and (move_component := self.components[0]).before.name.lower() == "p"
            and abs(move_component.before.col_indx - move_component.after.col_indx) == 2
        ):
            # Moved pawn two forward, so the en passant square is the square behind the pawn
            return (
                move_component.after.col_indx,
                # The row of square behind the pawn is the middle of the row before and after move
                (move_component.before.row_indx + move_component.after.row_indx) // 2,
            )
        return None

    @property
    def promotes_pawn(self) -> bool:
        return any(move_component.after.name != move_component.before.name for move_component in self.components)
