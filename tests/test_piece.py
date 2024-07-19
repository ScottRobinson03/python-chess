from tests import perform_test

from src.backend.game import Game
from src.backend.piece import Piece
from src.backend.utils import STARTING_BOARD_FEN
from src.typings import PieceName

WHITE_PIECE_NAMES: list[PieceName] = ["P", "R", "N", "B", "Q", "K"]
BLACK_PIECE_NAMES: list[PieceName] = ["p", "r", "n", "b", "q", "k"]
ALL_PIECE_NAMES = WHITE_PIECE_NAMES + BLACK_PIECE_NAMES


def test_init() -> None:
    for piece_name in ALL_PIECE_NAMES:
        piece = Piece(piece_name, 0, 1)

        perform_test(
            "Correctly sets name",
            lambda x: getattr(x, "name"),
            piece,
            expected_response=piece_name,
        )
        perform_test(
            "Correctly sets col_indx",
            lambda x: getattr(x, "col_indx"),
            piece,
            expected_response=0,
        )
        perform_test(
            "Correctly sets row_indx",
            lambda x: getattr(x, "row_indx"),
            piece,
            expected_response=1,
        )


def test_properties() -> None:
    for piece_name in ALL_PIECE_NAMES:
        piece = Piece(piece_name, 0, 1)
        expected_colour = "BLACK" if piece_name in BLACK_PIECE_NAMES else "WHITE"

        perform_test(
            f"Correctly sets colour getter for {piece_name!r} piece",
            lambda x: getattr(x, "colour"),
            piece,
            expected_response=expected_colour,
        )
        perform_test(
            f"Correctly sets color alias for {piece_name!r} piece",
            lambda x: getattr(x, "color"),
            piece,
            expected_response=expected_colour,
        )

    for row_indx in range(8):
        for col_indx in range(8):
            piece = Piece("p", col_indx, row_indx)
            expected_col = "abcdefgh"[col_indx]
            expected_position = f"{expected_col}{row_indx + 1}"

            perform_test(
                f"Correctly sets row for piece at {col_indx=}, {row_indx=}",
                lambda x: getattr(x, "row"),
                piece,
                expected_response=row_indx + 1,
            )
            perform_test(
                f"Correctly sets col for piece at {col_indx=}, {row_indx=}",
                lambda x: getattr(x, "col"),
                piece,
                expected_response=expected_col,
            )
            perform_test(
                f"Correctly sets position for piece at {col_indx=}, {row_indx=}",
                lambda x: getattr(x, "position"),
                piece,
                expected_response=expected_position,
            )


def test_move_generation() -> None:
    # TODO: Add tests for pawn promotion
    # TODO: Add tests for en-passant
    move_tests = [
        ("White pawn (can move double at start of game)", STARTING_BOARD_FEN, "a2", ["Pa2a3", "Pa2a4"]),
        ("White pawn (can't move double on non-first move)", "4k3/8/8/8/8/P7/8/4K3 w - - 0 1", "a3", ["Pa3a4"]),
        (  # Black pawn (can move double at start of game)
            "Black pawn (can move double at start of game)",
            STARTING_BOARD_FEN.replace("w", "b"),
            "a7",
            ["pa7a6", "pa7a5"],
        ),
        ("Black pawn (can't move double on non-first move)", "4k3/8/8/8/8/p7/8/4K3 b - - 0 1", "a3", ["pa3a2"]),
        ("White knight (start of game)", STARTING_BOARD_FEN, "b1", ["Nb1a3", "Nb1c3"]),
        ("Black knight (start of game)", STARTING_BOARD_FEN.replace("w", "b"), "b8", ["nb8a6", "nb8c6"]),
        (  # White knight (generates all directions & passes over pieces)
            "White knight (generates all directions & passes over pieces)",
            "4k3/8/3pPp2/3nNQ2/3RRR2/8/8/4K3 w - - 0 1",
            "e5",
            ["Ne5d3", "Ne5c4", "Ne5c6", "Ne5d7", "Ne5f7", "Ne5g6", "Ne5g4", "Ne5f3"],
        ),
        (  # White bishop (can't pass through own or enemy piece)
            "White bishop (can't pass through own or enemy piece)",
            "5k2/8/5n2/1Q6/2B5/8/8/4K3 w - - 0 1",
            "c4",
            [
                "Bc4b3",
                "Bc4a2",
                "Bc4d3",
                "Bc4e2",
                "Bc4f1",
                "Bc4d5",
                "Bc4e6",
                "Bc4f7",
                "Bc4g8",
            ],
        ),
        (  # White rook (queen-side castling)
            "White rook (queen-side castling)",
            "3k4/8/8/8/8/8/P7/R3K3 w Q - 0 1",
            "a1",
            [["Ra1b1"], ["Ra1c1"], ["Ra1d1+"], ["Ra1d1+", "Ke1c1"]],
        ),
        (  # Black rook (king-side castling)
            "Black rook (king-side castling)",
            "4k2r/7p/8/8/8/8/8/5K2 b k - 0 1",
            "h8",
            [["rh8g8"], ["rh8f8+"], ["rh8f8+", "ke8g8"]],
        ),
        (  # Black rook (can't pass through check when castling)
            "Black rook (can't pass through check when castling)",
            "4k2r/7p/8/8/8/8/8/4KQ2 b k - 0 1",
            "h8",
            ["rh8g8", "rh8f8"],
        ),
        (  # White queen (can't castle in position rook can)
            "White queen (can't castle in position rook can)",
            "3k4/8/8/8/8/8/PP6/Q3K3 w Q - 0 1",
            "a1",
            ["Qa1b1", "Qa1c1", "Qa1d1+"],
        ),
        (  # Black queen (can't move through pieces)
            "Black queen (can't move through pieces)",
            "4K3/5R2/8/2bq4/8/8/3k4/8 b - - 0 1",
            "d5",
            [
                # Up and left
                "qd5c6+",
                "qd5b7",
                "qd5a8+",
                # Up
                "qd5d6",
                "qd5d7+",
                "qd5d8+",
                # Up and right
                "qd5e6+",
                "qd5xf7+",
                # Right
                "qd5e5+",
                "qd5f5",
                "qd5g5",
                "qd5h5",
                # Down and right
                "qd5e4+",
                "qd5f3",
                "qd5g2",
                "qd5h1",
                # Down,
                "qd5d4",
                "qd5d3",
                # Down and left
                "qd5c4",
                "qd5b3",
                "qd5a2",
            ],
        ),
        (  # Black queen (can't make move if leaves self in check)
            "Black queen (can't make move if leaves self in check)",
            "4K3/3R4/8/2bq4/8/8/3k4/8 b - - 0 1",
            "d5",
            ["qd5d4", "qd5d3", "qd5d6", "qd5xd7+"],
        ),
        (  # White rook (checkmate detection with & without castling)
            "White rook (checkmate detection with & without castling)",
            "5kr1/4p1p1/8/8/Q7/8/7P/4K2R w K - 0 1",
            "h1",
            [["Rh1g1"], ["Rh1f1#"], ["Rh1f1#", "Ke1g1"]],
        ),
        (  # Black rook (checkmate detection with & without castling)
            "Black rook (checkmate detection with & without castling)",
            "4k2r/7p/8/8/7q/8/4P1P1/5KR1 b k - 0 1",
            "h8",
            [["rh8g8"], ["rh8f8#"], ["rh8f8#", "ke8g8"]],
        ),
        (  # White king (queen-side castling)
            "White king (queen-side castling)",
            "4k3/8/8/8/8/8/3PPP2/R3KB2 w Q - 0 1",
            "e1",
            [["Ke1d1"], ["Ke1c1", "Ra1d1"]],
        ),
        (  # White king (king-side castling)
            "White king (king-side castling)",
            "4k3/8/8/8/8/8/3PPP2/3QK2R w K - 0 1",
            "e1",
            [["Ke1f1"], ["Ke1g1", "Rh1f1"]],
        ),
        (  # Black king (queen-side castling)
            "Black king (queen-side castling)",
            "r3kb2/3ppp2/8/8/8/8/8/4K3 b q - 0 1",
            "e8",
            [["ke8d8"], ["ke8c8", "ra8d8"]],
        ),
        (  # Black king (king-side castling)
            "Black king (king-side castling)",
            "3qk2r/3ppp2/8/8/8/8/8/4K3 b k - 0 1",
            "e8",
            [["ke8f8"], ["ke8g8", "rh8f8"]],
        ),
    ]

    for test_name, board_fen, piece_position, expected_moves in move_tests:
        game = Game(board_fen)

        piece = game.board.get_piece_at(piece_position)
        if not piece:
            raise ValueError(f"Piece at {piece_position!r} is None")

        moves = [*piece.generate_possible_moves(game.board)]

        perform_test(test_name, lambda x: x, moves, expected_response=expected_moves, ignore_order=True)
