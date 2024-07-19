from __future__ import annotations
import traceback
from collections.abc import Generator
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    from src.backend.board import Board
from src.backend import utils
from src.backend.move import Move
from src.typings import (
    CheckmatesEnemy,
    ChecksEnemy,
    Colour,
    Column,
    ColumnIndex,
    PieceName,
    Position,
    RawMove,
    Row,
    RowIndex,
)


class Piece:
    can_castle: bool
    moved_double: bool
    col_indx: int
    name: PieceName
    row_indx: int

    def __init__(self, name: PieceName, col_indx: int, row_indx: int) -> None:
        self.name = name

        if not (0 <= col_indx < 8):
            raise ValueError(f"col_indx must be 0..7, but got {col_indx=}")
        if not (0 <= row_indx < 8):
            raise ValueError(f"row_indx must be 0..7, but got {row_indx=}")
        self.col_indx = col_indx
        self.row_indx = row_indx

        # Piece is deemed to be able to castle if it's a king or rook in its starting position.
        # Note that this ignores whether the king has ever been in check, since this is handled via CHECKED event.
        # Also ignores whether the piece has moved before, and whether the king would move through check,
        # since those are both handled within the respective move generation functions.
        self.can_castle = self.algebraic_position in {"ke8", "Ke1"} or self.algebraic_position in {
            "ra8",
            "rh8",
            "Ra1",
            "Rh1",
        }
        self.moved_double = False

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        if isinstance(other, Piece):
            return self.col_indx == other.col_indx and self.row_indx == other.row_indx and self.name == other.name

        raise NotImplementedError(f"Can't compare Piece with type {type(other).__name__!r}")

    def __repr__(self) -> str:
        return f"Piece({self.colour}, {self.name}, {self.col_indx}, {self.row_indx})"

    def __str__(self) -> str:
        return self.algebraic_position

    @staticmethod
    def _check_enemy_in_check_or_checkmate(
        board: Board, own_pieces: list[Piece], enemy_king: Piece
    ) -> tuple[ChecksEnemy, CheckmatesEnemy]:
        enemy_in_check: bool = False
        enemy_in_checkmate: bool = False
        for own_piece in own_pieces:
            if own_piece.can_move_to(enemy_king.row_indx, enemy_king.col_indx, board):
                enemy_in_check = True
                break

        if enemy_in_check:
            enemy_in_checkmate = True
            for _ in board.generate_possible_moves(for_opponent=enemy_king.colour != board.turn):
                # There's at least one possible move for the opponent, so they're not in checkmate.
                enemy_in_checkmate = False
                break

        return enemy_in_check, enemy_in_checkmate

    @staticmethod
    def _get_board_after_raw_moves(board: Board, raw_moves: list[RawMove]) -> Board:
        new_board = deepcopy(board)

        piece_captured: bool = False
        pawn_moved: bool = False

        for raw_move in raw_moves:
            old_piece, new_piece, captured_piece = raw_move

            if old_piece.name.lower() == "p":
                pawn_moved = True

            if new_board.squares[old_piece.row_indx][old_piece.col_indx] != old_piece:
                if new_board.squares[new_piece.row_indx][new_piece.col_indx] != new_piece:
                    raise ValueError(
                        f"Move {raw_move} expected {old_piece!r} to be at {old_piece.col_indx, old_piece.row_indx}, but it's not:\n{new_board}\n{board}"
                    )
                print(
                    f"WARNING: {old_piece!r} was already moved to {new_piece.col_indx, new_piece.row_indx}.\n{new_board}\n{board}"
                )
            new_board.squares[old_piece.row_indx][old_piece.col_indx] = None

            if (
                (existing_piece_at_new_square := new_board.squares[new_piece.row_indx][new_piece.col_indx]) is not None
                and existing_piece_at_new_square != new_piece
                and captured_piece is None
            ):
                raise ValueError(
                    f"New square for {old_piece!r} was unexpectedly occupied by another piece: {existing_piece_at_new_square!r}."
                )

            if captured_piece is not None:
                piece_captured = True
                # We have to manually remove the taken piece from the corresponding list(s) of pieces, as it's not done automatically.
                if captured_piece.colour == old_piece.colour:
                    raise ValueError(
                        f"Expected {old_piece!r} to take an enemy piece, but found own piece at new location: {captured_piece!r}."
                    )
                if captured_piece.colour == "WHITE":
                    new_board.white_pieces.all.remove(captured_piece)
                    if captured_piece.name == "R":
                        new_board.white_pieces.rooks.remove(captured_piece)
                else:
                    new_board.black_pieces.all.remove(captured_piece)
                    if captured_piece.name == "r":
                        new_board.black_pieces.rooks.remove(captured_piece)

                if not (
                    captured_piece.row_indx == new_piece.row_indx and captured_piece.col_indx == new_piece.col_indx
                ):
                    if not (new_piece.name.lower() == "p" and captured_piece.name.lower() == "p"):
                        raise ValueError(
                            f"Expected {old_piece!r} to be taking a pawn via en-passant, but it's actually capturing {captured_piece!r}."
                        )
                    new_board.squares[captured_piece.row_indx][captured_piece.col_indx] = None

            new_board.squares[new_piece.row_indx][new_piece.col_indx] = new_piece

            # Note we again have to update the piece containers manually.
            if new_piece.colour == "WHITE":
                try:
                    new_board.white_pieces.all[new_board.white_pieces.all.index(old_piece)] = new_piece
                    if new_piece.name == "R":
                        new_board.white_pieces.rooks[new_board.white_pieces.rooks.index(old_piece)] = new_piece
                    elif new_piece.name == "K":
                        new_board.white_pieces.king = new_piece
                except Exception as e:
                    print(traceback.print_exception(e))
                    raise e
            else:
                new_board.black_pieces.all[new_board.black_pieces.all.index(old_piece)] = new_piece
                if new_piece.name == "r":
                    new_board.black_pieces.rooks[new_board.black_pieces.rooks.index(old_piece)] = new_piece
                elif new_piece.name == "k":
                    new_board.black_pieces.king = new_piece

        if pawn_moved or piece_captured:
            new_board.halfmove_clock = 0
        else:
            new_board.halfmove_clock += 1

        if new_board.turn == "BLACK":
            new_board.fullmove_number += 1
            new_board.turn = "WHITE"
        else:
            new_board.turn = "BLACK"
        return new_board

    @overload
    def generate_possible_moves(
        self, board: Board, *, check_for_checks: Literal[True] = True
    ) -> Generator[Move, Any, None]: ...
    @overload
    def generate_possible_moves(
        self, board: Board, *, check_for_checks: Literal[False]
    ) -> Generator[list[RawMove], Any, None]: ...
    def generate_possible_moves(
        self, board: Board, *, check_for_checks: bool = True
    ) -> Generator[Move | list[RawMove], Any, None]:
        name_lower = self.name.lower()

        for raw_moves in (
            self._pawn_moves(board)
            if name_lower == "p"
            else self._knight_moves(board)
            if name_lower == "n"
            else self._bishop_moves(board)
            if name_lower == "b"
            else self._rook_moves(board)
            if name_lower == "r"
            else self._queen_moves(board)
            if name_lower == "q"
            else self._king_moves(board)
        ):
            if check_for_checks is False:
                # Currently in a fake-state that's part of checking for what was originally self-check.
                # This means we don't need to care about self/enemy being in check.
                yield raw_moves
                continue

            if len(raw_moves) == 1:
                _, new_piece, move_takes_enemy_piece = raw_moves[0]
                new_row_indx, new_col_indx = new_piece.row_indx, new_piece.col_indx
            else:
                # The only situation where multiple pieces are moved at once is castling.
                # For castling we don't need to check if self in check since that's done in move generation.
                # We do however need to check if the enemy is now in check/checkmate,
                # but we only need to check that the rook that was castled with is checking enemy.
                rooks_moved = [*filter(lambda x: x[1].name.lower() == "r", raw_moves)]
                if len(rooks_moved) == 0:
                    raise ValueError("Failed to find the rook that was moved when castling.")
                if len(rooks_moved) > 1:
                    raise ValueError("Multiple rooks were somehow moved when castling.")
                rook_castled_with_after_move = rooks_moved[0][1]

                board_after_castling = Piece._get_board_after_raw_moves(board, raw_moves)

                enemy_king = (
                    board_after_castling.black_pieces if self.colour == "WHITE" else board_after_castling.white_pieces
                ).king

                enemy_in_check, enemy_in_checkmate = Piece._check_enemy_in_check_or_checkmate(
                    board_after_castling, [rook_castled_with_after_move], enemy_king
                )

                yield Move.from_raw_moves(
                    [
                        *map(
                            # Only mark the rook as initiating check/checkmate
                            lambda raw_move: (raw_move, enemy_in_check, enemy_in_checkmate)
                            if raw_move[0].name.lower() == "r"
                            else (raw_move, False, False),
                            raw_moves,
                        )
                    ]
                )
                continue

            if move_takes_enemy_piece:
                if (
                    piece_taken := board.squares[new_row_indx][new_col_indx]
                ) is not None and piece_taken.name.lower() == ("k" if self.colour == "WHITE" else "K"):
                    # Directly taking enemy king, so never any reason could be invalid.
                    yield Move.from_raw_moves([(raw_moves[0], True, True)])
                    continue

            # First move in chain, so check whether WE will be in check after move,
            # and if not then whether the ENEMY will be in check after move.
            board_after_move = Piece._get_board_after_raw_moves(board, raw_moves)

            own_pieces_container = (
                board_after_move.white_pieces if self.colour == "WHITE" else board_after_move.black_pieces
            )
            own_pieces = own_pieces_container.all
            own_king = own_pieces_container.king

            enemy_pieces_container = (
                board_after_move.black_pieces if self.colour == "WHITE" else board_after_move.white_pieces
            )
            enemy_pieces = enemy_pieces_container.all
            enemy_king = enemy_pieces_container.king

            self_in_check: bool = False
            for enemy_piece in enemy_pieces:
                if enemy_piece.can_move_to(own_king.row_indx, own_king.col_indx, board_after_move):
                    self_in_check = True
                    break

            if self_in_check:
                # We'd be in check after this move, and aren't taking enemy king, so can't make move.
                continue

            # We won't be in check ourselves after this move, so check whether the enemy would be:
            enemy_in_check, enemy_in_checkmate = Piece._check_enemy_in_check_or_checkmate(
                board_after_move, own_pieces, enemy_king
            )
            yield Move.from_raw_moves([(raw_moves[0], enemy_in_check, enemy_in_checkmate)])

    def _bishop_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        for row_offset in range(-1, 2, 2):
            for col_offset in range(-1, 2, 2):
                for i in range(1, 8):
                    if not (
                        (new_row_indx := self.row_indx + i * row_offset) in range(8)
                        and (new_col_indx := self.col_indx + i * col_offset) in range(8)
                    ):
                        # Would be off the board, so stop
                        break

                    if (captured_piece := board.squares[new_row_indx][new_col_indx]) is None:
                        # The space is empty
                        new_self = Piece(self.name, new_col_indx, new_row_indx)
                        yield [(self, new_self, captured_piece)]
                        continue
                    # The space isn't empty, so check if it's a piece we can take.
                    if captured_piece.colour != self.colour:
                        new_self = Piece(self.name, new_col_indx, new_row_indx)
                        yield [(self, new_self, captured_piece)]
                    break  # We can't move past another piece

    def _king_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        for row_offset in range(-1, 2):
            for col_offset in range(-1, 2):
                if row_offset == col_offset == 0:
                    # Can't move to the same position
                    continue

                if not (
                    (new_row_indx := self.row_indx + row_offset) in range(8)
                    and (new_col_indx := self.col_indx + col_offset) in range(8)
                ):
                    # Would be off the board, so stop
                    continue

                if (
                    captured_piece := board.squares[new_row_indx][new_col_indx]
                ) is None or captured_piece.colour != self.colour:
                    new_self = Piece(self.name, new_col_indx, new_row_indx)
                    new_self.can_castle = False  # Can no longer castle after moving
                    yield [(self, new_self, captured_piece)]

        # Castling
        own_rooks = (board.white_pieces if self.colour == "WHITE" else board.black_pieces).rooks
        for rook in own_rooks:
            if Piece.can_castle_with(self, rook, board):
                castling_col_direction = 1 if rook.col_indx > self.col_indx else -1

                new_king_col_indx = self.col_indx + 2 * castling_col_direction
                new_king = Piece(self.name, new_king_col_indx, self.row_indx)

                # If rook is queen-side then it moves 3 squares not 2
                rook_col_offset = 3 if rook.col_indx < self.col_indx else 2
                new_rook_col_indx = rook.col_indx - rook_col_offset * castling_col_direction
                new_rook = Piece(rook.name, new_rook_col_indx, rook.row_indx)

                yield [(self, new_king, None), (rook, new_rook, None)]

    def _knight_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        # Moving two rows and one column
        for row_offset in range(-2, 3, 4):
            for col_offset in range(-1, 2, 2):
                if not (
                    (new_row_indx := self.row_indx + row_offset) in range(8)
                    and (new_col_indx := self.col_indx + col_offset) in range(8)
                ):
                    # Would be off the board, so stop
                    continue

                if (
                    captured_piece := board.squares[new_row_indx][new_col_indx]
                ) is None or captured_piece.colour != self.colour:
                    new_self = Piece(self.name, new_col_indx, new_row_indx)
                    yield [(self, new_self, captured_piece)]

        # Moving two columns and one row
        for row_offset in range(-1, 2, 2):
            for col_offset in range(-2, 3, 4):
                if not (
                    (new_row_indx := self.row_indx + row_offset) in range(8)
                    and (new_col_indx := self.col_indx + col_offset) in range(8)
                ):
                    # Would be off the board, so stop
                    continue

                if (
                    captured_piece := board.squares[new_row_indx][new_col_indx]
                ) is None or captured_piece.colour != self.colour:
                    new_self = Piece(self.name, new_col_indx, new_row_indx)
                    yield [(self, new_self, captured_piece)]

    def _pawn_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        row_offset = 1 if self.colour == "WHITE" else -1
        if (new_row_indx := self.row_indx + row_offset) not in range(8):
            # Would be off the board, so stop. Note that this situation
            # shouldn't ever happen, as should have promoted to a different piece.
            # return
            raise ValueError(f"Somehow ended up with a non-promoted pawn on the end row: {self!r}.")

        # Forward Move
        if board.squares[new_row_indx][self.col_indx] is None:
            # TODO: Allow player to choose promotion piece
            new_name = self.name if new_row_indx not in {0, 7} else "Q" if self.colour == "WHITE" else "q"
            new_self = Piece(new_name, self.col_indx, new_row_indx)
            yield [(self, new_self, None)]

            # Double Forward Move
            if (
                (self.row == 2 and self.colour == "WHITE") or (self.row == 7 and self.colour == "BLACK")
            ) and board.squares[(double_forward_row_indx := self.row_indx + 2 * row_offset)][self.col_indx] is None:
                # Is in starting position and the two spaces infront is clear
                new_self = Piece(self.name, self.col_indx, double_forward_row_indx)
                new_self.moved_double = True
                yield [(self, new_self, None)]

        # Diagonal Move
        for col_offset in range(-1, 2, 2):
            if not 0 <= (new_col_indx := self.col_indx + col_offset) <= 7:
                # Would be off the board, so skip
                continue

            new_name = self.name if new_row_indx not in {0, 7} else "Q" if self.colour == "WHITE" else "q"

            if (
                captured_piece := board.squares[new_row_indx][new_col_indx]
            ) is not None and captured_piece.colour != self.colour:
                # There's an enemy piece that this pawn can take
                new_self = Piece(new_name, new_col_indx, new_row_indx)
                yield [(self, new_self, captured_piece)]

            # En Passant

            if (
                (en_passant_captured_piece := board.squares[self.row_indx][new_col_indx]) is not None
                and en_passant_captured_piece.colour != self.colour
                and en_passant_captured_piece.moved_double
                and board.prev_move
                and board.prev_move.ends_at(new_col_indx, self.row_indx)
            ):
                # There's an enemy pawn that we can take via en-passant
                new_self = Piece(new_name, new_col_indx, new_row_indx)
                yield [(self, new_self, en_passant_captured_piece)]

    def _queen_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        # Note: We can safely yield from rook moves despite rooks being able to castle and not queens,
        # since castling detection is hardcoded to only allow castling for kings and rooks (see `Piece.can_castle` attribute).
        yield from self._rook_moves(board)
        yield from self._bishop_moves(board)

    def _rook_moves(self, board: Board) -> Generator[list[RawMove], Any, None]:
        # Vertical Movement
        for row_offset in range(-1, 2):
            for i in range(1, 8):
                if (new_row_indx := self.row_indx + i * row_offset) not in range(8):
                    # Would be off the board, so stop
                    break

                if (captured_piece := board.squares[new_row_indx][self.col_indx]) is None:
                    # The space is empty
                    new_self = Piece(self.name, self.col_indx, new_row_indx)
                    new_self.can_castle = False  # Can no longer castle after moving
                    yield [(self, new_self, None)]
                    continue
                # The space isn't empty, so check if it's a piece we can take.
                if captured_piece.colour != self.colour:
                    new_self = Piece(self.name, self.col_indx, new_row_indx)
                    new_self.can_castle = False  # Can no longer castle after moving
                    yield [(self, new_self, captured_piece)]
                break  # We can't move past another piece

        # Horizontal Movement
        for col_offset in range(-1, 2):
            for i in range(1, 8):
                if (new_col_indx := self.col_indx + i * col_offset) not in range(8):
                    # Would be off the board, so stop
                    break

                if (captured_piece := board.squares[self.row_indx][new_col_indx]) is None:
                    # The space is empty
                    new_self = Piece(self.name, new_col_indx, self.row_indx)
                    new_self.can_castle = False  # Can no longer castle after moving
                    yield [(self, new_self, None)]
                    continue
                # The space isn't empty, so check if it's a piece we can take.
                if captured_piece.colour != self.colour:
                    new_self = Piece(self.name, new_col_indx, self.row_indx)
                    new_self.can_castle = False  # Can no longer castle after moving
                    yield [(self, new_self, captured_piece)]
                break  # We can't move past another piece

        # Castling
        own_king = (board.white_pieces if self.colour == "WHITE" else board.black_pieces).king
        if Piece.can_castle_with(own_king, self, board):
            # The king can castle with this rook
            castling_col_direction = -1 if self.col_indx > own_king.col_indx else 1

            # If we're castling queen-side, then rook moves 3 squares, else 2 squares.
            rook_col_offset = 3 if castling_col_direction == 1 else 2
            new_rook_col_indx = self.col_indx + rook_col_offset * castling_col_direction
            new_rook = Piece(self.name, new_rook_col_indx, self.row_indx)

            new_king_col_indx = own_king.col_indx - 2 * castling_col_direction
            new_king = Piece(own_king.name, new_king_col_indx, own_king.row_indx)

            yield [(self, new_rook, None), (own_king, new_king, None)]

    @staticmethod
    def can_castle_with(king: Piece, rook: Piece, board: Board) -> bool:
        if not (king.can_castle and rook.can_castle and king.colour == rook.colour):
            return False
        king_col_direction = 1 if rook.col_indx > king.col_indx else -1
        rook_col_direction = -1 * king_col_direction

        # King movement validation
        for col_offset in range(1, 3):
            new_king_col_indx = king.col_indx + col_offset * king_col_direction
            if board.squares[king.row_indx][new_king_col_indx] is not None:
                # There's a piece in the way of the king, so we can't castle with this rook
                return False

            # Kings can't castle through check, so we need to ensure we aren't in check in this midway position

            king_after_midway_move = Piece(king.name, new_king_col_indx, king.row_indx)
            cloned_board = king._get_board_after_raw_moves(board, [(king, king_after_midway_move, None)])

            # Check whether the king is in check
            enemy_pieces = (cloned_board.black_pieces if king.colour == "WHITE" else cloned_board.white_pieces).all
            for enemy_piece in enemy_pieces:
                if enemy_piece.can_move_to(
                    king_after_midway_move.row_indx, king_after_midway_move.col_indx, cloned_board
                ):
                    # Would be castling through check, so can't castle with this rook
                    return False

        # Rook movement validation

        # Rooks move 3 squares if castling queen-side, and 2 if castling king-side
        squares_to_move_for_rook = 3 if rook.col_indx < king.col_indx else 2
        for col_offset in range(1, squares_to_move_for_rook + 1):
            new_rook_col_indx = rook.col_indx + col_offset * rook_col_direction
            if board.squares[rook.row_indx][new_rook_col_indx] is not None:
                # There's a piece in the way of the rook, so we can't castle with this rook
                return False
        return True

    def can_move_to(self, wanted_row_indx: RowIndex, wanted_col_indx: ColumnIndex, board: Board) -> bool:
        for raw_moves in self.generate_possible_moves(board, check_for_checks=False):
            for _, new_piece, _ in raw_moves:
                if new_piece.row_indx == wanted_row_indx and new_piece.col_indx == wanted_col_indx:
                    return True
        return False

    @property
    def algebraic_position(self) -> str:
        return f"{self.name}{self.position}"

    @property
    def col(self) -> Column:
        return self.column

    @property
    def color(self) -> Colour:
        return self.colour

    @property
    def colour(self) -> Colour:
        return "WHITE" if self.name.isupper() else "BLACK"

    @property
    def column(self) -> Column:
        return utils.column_index_to_letter(self.col_indx)

    @property
    def enemy_color(self) -> Colour:
        return self.enemy_colour

    @property
    def enemy_colour(self) -> Colour:
        return "BLACK" if self.colour == "WHITE" else "WHITE"

    @property
    def position(self) -> Position:
        return f"{self.col}{self.row}"

    @property
    def row(self) -> Row:
        return self.row_indx + 1
