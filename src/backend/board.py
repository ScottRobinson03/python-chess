import random
from collections.abc import Generator
from typing import Any

from src.backend import utils
from src.backend.move import Move
from src.backend.piece import Piece
from src.backend.piece_container import PieceContainer
from src.typings import BoardList, Colour, Column, FenChar, PieceName


class Board:
    black_pieces: PieceContainer
    fen: str
    halfmove_clock: int = 0
    fullmove_number: int = 1
    prev_move: Move | None = None
    squares: BoardList
    turn: Colour
    white_pieces: PieceContainer

    def __init__(self, board_fen: str | None = None) -> None:
        if board_fen:
            # NB: Turn is determined by FEN in _generate_board_from_fen
            self._generate_board_from_fen(board_fen)
            self.fen = board_fen
        else:
            self.turn = random.choice(["WHITE", "BLACK"])
            self.fen = self._generate_random_board()
            print(f"Generated board: {self.fen}\n{self}\n")

    def __str__(self) -> str:
        board_as_str: str = ""
        for row in self.squares[::-1]:  # Reverse the board so that a1 is at the bottom left, not top left.
            board_as_str += " | ".join(str(col) if col else "   " for col in row)
            board_as_str += "\n"

        return board_as_str

    def _generate_board_from_fen(self, board_fen: str) -> None:
        board: BoardList = []

        # Parse the board from the FEN
        board_fen_split = board_fen.split(" ")
        if len(board_fen_split) != 6:
            raise ValueError(f"FEN string must have 6 segments, but got {len(board_fen_split)}: {board_fen!r}")

        board_fen_rows = board_fen_split[0].split("/")
        if len(board_fen_rows) != 8:
            raise ValueError(f"FEN piece placements must have 8 segments, but got {len(board_fen_rows)}: {board_fen!r}")

        white_pieces: list[Piece] = []
        white_king: Piece
        white_rooks: list[Piece] = []

        black_pieces: list[Piece] = []
        black_king: Piece
        black_rooks: list[Piece] = []

        for row_indx_offset, row in enumerate(board_fen_rows):
            # FEN notation has 8th row first so we subtract index from 7
            # so that first row from FEN has correct row index of 7, etc.
            row_indx = 7 - row_indx_offset

            board_row: list[Piece | None] = []
            col_indx: int = 0

            for char in row:  # type: ignore -- Python thinks `char` can't be a FenChar
                char: FenChar  # type: ignore -- Python doesn't like that we change type further down
                if char.isdigit():
                    num_empty_squares = int(char)
                    board_row.extend([None] * num_empty_squares)
                    col_indx += num_empty_squares
                    continue

                # `char` isn't a number, so it has to be a PieceName.
                # Unfortunately, Python doesn't automatically narrow this.
                char: PieceName

                piece = Piece(char, col_indx, row_indx)
                if piece.colour == "WHITE":
                    white_pieces.append(piece)
                    if piece.name == "R":
                        white_rooks.append(piece)
                    elif piece.name == "K":
                        white_king = piece
                else:
                    black_pieces.append(piece)
                    if piece.name == "r":
                        black_rooks.append(piece)
                    elif piece.name == "k":
                        black_king = piece

                board_row.append(piece)
                col_indx += 1

            # FEN notation has 8th row first so we insert rather than append
            # to ensure that 1st row is board[0] and 8th row is board[7]
            if len(board_row) != 8:
                raise ValueError(
                    f"FEN rows must have 8 pieces but FEN row with index {row_indx} has {len(board_fen)}: {row!r}"
                )
            board.insert(0, board_row)
        self.squares = board

        self.white_pieces = PieceContainer(white_pieces, white_king, white_rooks)
        self.black_pieces = PieceContainer(black_pieces, black_king, black_rooks)

        # Parse the remainder of the FEN
        turn, castling_rights, en_passant_square, halfmove_clock, fullmove_number = board_fen_split[1:]

        # Parse turn
        if turn not in ("w", "b"):
            raise ValueError(f"Turn must be 'w' for white or 'b' for black, but got {turn!r}")
        self.turn = "WHITE" if turn == "w" else "BLACK"

        # Parse castling rights
        if castling_rights == "-":
            # No castling rights, so update the kings and rooks to not be able to castle.
            self.white_pieces.king.can_castle = False
            self.black_pieces.king.can_castle = False
            for rook in [*self.white_pieces.rooks, *self.black_pieces.rooks]:
                rook.can_castle = False
        else:
            if "K" not in castling_rights:
                # White can't castle kingside, so update the kingside rook to not be able to castle.
                # Note that we only look at h1 since if kingside rook isn't there then can_castle will
                # be False anyway since the rook has moved from its start position.
                kingside_rook = self.get_piece_at("h1")
                if kingside_rook:
                    kingside_rook.can_castle = False
            if "Q" not in castling_rights:
                # White can't castle queenside, so update the queenside rook to not be able to castle.
                # Note that we only look at a1 since if queenside rook isn't there then can_castle will
                # be False anyway since the rook has moved from its start position.
                queenside_rook = self.get_piece_at("a1")
                if queenside_rook:
                    queenside_rook.can_castle = False
            if "k" not in castling_rights:
                # Black can't castle kingside, so update the kingside rook to not be able to castle.
                # Note that we only look at h8 since if kingside rook isn't there then can_castle will
                # be False anyway since the rook has moved from its start position.
                kingside_rook = self.get_piece_at("h8")
                if kingside_rook:
                    kingside_rook.can_castle = False
            if "q" not in castling_rights:
                # Black can't castle queenside, so update the queenside rook to not be able to castle.
                # Note that we only look at a8 since if queenside rook isn't there then can_castle will
                # be False anyway since the rook has moved from its start position.
                queenside_rook = self.get_piece_at("a8")
                if queenside_rook:
                    queenside_rook.can_castle = False

        # Parse en passant target square
        if en_passant_square != "-":
            # En passant square is only set when the previous move was a pawn moving two squares,
            # so we can set the previous move to be an opponent pawn moving two squares.
            pawn_row_indx_after = 3 if self.turn == "BLACK" else 4
            piece_name: PieceName = "P" if self.turn == "BLACK" else "p"
            col_letter: Column = en_passant_square[0]  #  type: ignore
            pawn_col_indx = utils.letter_to_column_index(col_letter)

            pawn_after = board[pawn_row_indx_after][pawn_col_indx]
            if pawn_after is None:
                raise ValueError(
                    f"FEN en passant target square {en_passant_square!r} is not valid since there is no pawn at the would-be new pawn location."
                )

            pawn_row_indx_before = 1 if self.turn == "BLACK" else 6
            pawn_before = Piece(piece_name, pawn_col_indx, pawn_row_indx_before)

            self.prev_move = Move.from_raw_moves(
                [
                    (
                        (
                            pawn_before,
                            pawn_after,
                            None,
                        ),
                        False,
                        False,
                    )
                ]
            )

        # Parse halfmove clock and fullmove number
        self.halfmove_clock = int(halfmove_clock)
        self.fullmove_number = int(fullmove_number)

    def _generate_fen(self) -> str:
        fen: str = ""

        # Add pieces to FEN
        for row_count, row in enumerate(self.squares[::-1], start=1):
            empty_squares = 0
            for piece in row:
                if piece is None:
                    empty_squares += 1
                else:
                    if empty_squares:
                        fen += str(empty_squares)
                        empty_squares = 0
                    fen += piece.name

            if empty_squares:
                fen += str(empty_squares)
            if row_count < 8:
                fen += "/"

        # Add turn to FEN
        fen += f" {self.turn[0].lower()} "

        # Add castling rights to FEN
        if self.white_pieces.king.can_castle:
            kingside_rook = self.get_piece_at("h1")
            if kingside_rook and kingside_rook.can_castle:
                fen += "K"
            queenside_rook = self.get_piece_at("a1")
            if queenside_rook and queenside_rook.can_castle:
                fen += "Q"
        if self.black_pieces.king.can_castle:
            kingside_rook = self.get_piece_at("h8")
            if kingside_rook and kingside_rook.can_castle:
                fen += "k"
            queenside_rook = self.get_piece_at("a8")
            if queenside_rook and queenside_rook.can_castle:
                fen += "q"

        # Add en passant square to FEN (if applicable)
        if self.prev_move and self.prev_move.en_passant_square:
            col_indx, row_indx = self.prev_move.en_passant_square
            fen += f" {utils.column_index_to_letter(col_indx)}{row_indx + 1} "
        else:
            fen += " - "

        # Add halfmove clock and fullmove number to FEN
        fen += f"{self.halfmove_clock} {self.fullmove_number}"

        return fen

    def _generate_random_board(self) -> str:
        print("Generating random board. This may take some time...")

        colours: list[Colour] = ["WHITE", "BLACK"]
        piece_names_lower: list[PieceName] = ["p", "q", "r", "b", "n"]

        # It's more likely to have fewer than more of the same piece,
        # so we use decreasing weights on occurences (with exception of no occurence).
        weights_for_pawns = [5, 15, 45, 25, 5, 2, 1.5, 1, 0.5]
        weights_for_queens = [35, 45, 10, 5, 2, 1.25, 0.875, 0.5, 0.25, 0.125]
        weights_for_rooks_knights_bishops = [10, 35, 35, 10, 5, 2, 1.25, 0.875, 0.5, 0.25, 0.125]

        board_valid: bool = False
        attempt: int = 0
        while not board_valid:
            attempt += 1
            if attempt % 10 == 0:
                print(f"Attempt {attempt}...")

            white_pieces: list[Piece] = []
            white_king: Piece
            white_rooks: list[Piece] = []

            black_pieces: list[Piece] = []
            black_king: Piece
            black_rooks: list[Piece] = []

            board: BoardList = [[None for _ in range(8)] for _ in range(8)]

            for colour in colours:
                num_pawns = random.choices(range(8 + 1), k=1, weights=weights_for_pawns)[0]

                max_num_queens = 1 + (8 - num_pawns)
                num_queens = random.choices(
                    range(max_num_queens + 1), k=1, weights=weights_for_queens[: max_num_queens + 1]
                )[0]

                max_num_rooks = 2 + max((8 - num_pawns - num_queens), 0)
                num_rooks = random.choices(
                    range(max_num_rooks + 1),
                    k=1,
                    weights=weights_for_rooks_knights_bishops[: max_num_rooks + 1],
                )[0]

                max_num_bishops = 2 + max((8 - num_pawns - num_queens - num_rooks, 0))
                num_bishops = random.choices(
                    range(max_num_bishops + 1),
                    k=1,
                    weights=weights_for_rooks_knights_bishops[: max_num_bishops + 1],
                )[0]

                max_num_knights = 2 + max((8 - num_pawns - num_queens - num_rooks - num_bishops), 0)
                num_knights = random.choices(
                    range(max_num_knights + 1),
                    k=1,
                    weights=weights_for_rooks_knights_bishops[: max_num_knights + 1],
                )[0]

                piece_counts = (num_pawns, num_queens, num_rooks, num_bishops, num_knights)

                for indx, num_of_piece in enumerate(piece_counts):
                    for _ in range(num_of_piece):
                        piece_name_lower = piece_names_lower[indx]

                        while True:
                            # Find a free square for this piece
                            piece_row_indx = random.randint(1, 6) if piece_name_lower == "p" else random.randint(0, 7)
                            piece_col_indx = random.randint(0, 7)
                            if board[piece_row_indx][piece_col_indx] is None:
                                break

                        if colour == "WHITE":
                            piece_name: PieceName = piece_name_lower.upper()  # type: ignore -- Python doesn't realise that uppercase piece name is still a piece name
                            piece = Piece(piece_name, piece_col_indx, piece_row_indx)
                            white_pieces.append(piece)
                            if piece_name == "R":
                                white_rooks.append(piece)
                        else:
                            piece = Piece(piece_name_lower, piece_col_indx, piece_row_indx)
                            black_pieces.append(piece)
                            if piece_name_lower == "r":
                                black_rooks.append(piece)

                        board[piece_row_indx][piece_col_indx] = piece

                while True:
                    # Find a free square for the king
                    king_row_indx = random.randint(0, 7)
                    king_col_indx = random.randint(0, 7)
                    if board[king_row_indx][king_col_indx] is None:
                        break

                if colour == "WHITE":
                    white_king = Piece("K", king_col_indx, king_row_indx)
                    white_pieces.append(white_king)
                    board[king_row_indx][king_col_indx] = white_king
                else:
                    black_king = Piece("k", king_col_indx, king_row_indx)
                    black_pieces.append(black_king)
                    board[king_row_indx][king_col_indx] = black_king

            self.white_pieces = PieceContainer(white_pieces, white_king, white_rooks)
            self.black_pieces = PieceContainer(black_pieces, black_king, black_rooks)
            self.squares = board

            # Prevent white and black from starting in check
            for own_move in self.generate_possible_moves():
                if own_move.captured_piece is not None and own_move.captured_piece.name.lower() == "k":
                    break
            else:
                for opponent_move in self.generate_possible_moves(for_opponent=True):
                    if opponent_move.captured_piece is not None and opponent_move.captured_piece.name.lower() == "k":
                        break
                else:
                    board_valid = True

        fen = self._generate_fen()
        print(f"Generated random board in {attempt} attempts.")
        return fen

    def generate_possible_moves(self, *, for_opponent: bool = False) -> Generator[Move, Any, None]:
        pieces_of_turn = (
            self.white_pieces
            if (self.turn == "WHITE" and not for_opponent) or (self.turn == "BLACK" and for_opponent)
            else self.black_pieces
        ).all
        for piece in pieces_of_turn:
            yield from piece.generate_possible_moves(self)

    def get_piece_at(self, position: str) -> Piece | None:
        if len(position) != 2:
            raise ValueError(
                f"Position must be a string of length 2, but got a string of length {len(position)}: {position!r}"
            )

        if position[0] not in "abcdefgh":
            raise ValueError(f"Position must start with the column (one of 'abcdefgh'), but got {position[0]!r}")

        if position[1] not in "12345678":
            raise ValueError(f"Position must end with the row (one of '12345678'), but got {position[1]!r}")

        col_indx = "abcdefgh".index(position[0])
        row_indx = int(position[1]) - 1
        return self.squares[row_indx][col_indx]

    @property
    def pieces(self) -> list[Piece]:
        return self.white_pieces.all + self.black_pieces.all
