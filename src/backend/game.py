from enum import Enum

from src.backend.board import Board
from src.backend.move import Move
from src.backend.piece import Piece
from src.backend.utils import STARTING_BOARD_FEN


class DrawReason(Enum):
    FIFTY_MOVE_RULE = "fifty-move rule"
    INSUFFICIENT_MATERIAL = "insufficient material"
    REPITITION = "repitition"
    STALEMATE = "stalemate"


class Game:
    def __init__(self, board_fen: str | None = None) -> None:
        self.board: Board = Board(board_fen)
        self.fens: list[str] = [self.board.fen]
        self.over = False

    def perform_move(self, move: Move) -> DrawReason | None:
        new_board = Piece._get_board_after_raw_moves(self.board, move.to_raw_moves())
        new_board.prev_move = move
        self.board = new_board
        new_fen = new_board._generate_fen()
        self.fens.append(new_fen)

        # Check for repitition
        count: int = 0
        for fen in self.fens:
            # NB: We only need to check the first 4 parts of the FEN string
            # since halfmove counter and fullmove number don't have to match
            if fen.split(" ")[:4] == new_fen.split(" ")[:4]:
                if count == 2:
                    # This is the third occurence of the same state, so it's a draw by repitition
                    self.over = True
                    return DrawReason.REPITITION
                count += 1

        # Check for checkmate
        if move.checkmates_enemy:
            self.over = True
            return None

        # Check for stalemate
        can_move: bool = False
        for move in self.board.generate_possible_moves():
            can_move = True
            break
        if not can_move:
            # Stalemate as opponent is not in check but has no legal moves
            self.over = True
            return DrawReason.STALEMATE

        # Check for fifty-move rule
        if self.board.halfmove_clock >= 50:
            self.over = True
            return DrawReason.FIFTY_MOVE_RULE

        # Check for insufficient material
        # NB: Covering every single scenario where there's insufficient material to checkmate
        # is actually incredibly difficult, so we just cover the most simple ones.
        if self.board.prev_move and self.board.prev_move.captures_piece:
            remaining_white_pieces = self.board.white_pieces.all
            remaining_black_pieces = self.board.black_pieces.all
            if len(remaining_white_pieces) == 1 and len(remaining_black_pieces) == 1:
                # Only the two kings left
                self.over = True
                return DrawReason.INSUFFICIENT_MATERIAL

            white_has_sufficient = len(remaining_white_pieces) > 2 or any(
                piece.name in "PQR" for piece in remaining_white_pieces
            )
            black_has_sufficient = len(remaining_black_pieces) > 2 or any(
                piece.name in "pqr" for piece in remaining_black_pieces
            )
            if not (white_has_sufficient or black_has_sufficient):
                # Neither side has sufficient material to checkmate (require at least king + 2 or king + p/r/q)
                self.over = True
                return DrawReason.INSUFFICIENT_MATERIAL

        return None


if __name__ == "__main__":
    bm = Game(STARTING_BOARD_FEN)
    print(bm.board)
    print(bm.board._generate_fen())
    print([*bm.board.generate_possible_moves()])
