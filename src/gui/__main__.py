from enum import Enum
from typing import Any

import pygame

from src.backend.board import Board
from src.backend.game import Game
from src.backend.move import Move
from src.backend.piece import Piece
from src.backend.utils import STARTING_BOARD_FEN  # noqa
from src.typings import ColumnIndex, RowIndex

SCREEN_WIDTH = 512
SCREEN_HEIGHT = 512
SQUARE_SIDE_LENGTH = 64

if SQUARE_SIDE_LENGTH * 8 > SCREEN_WIDTH or SQUARE_SIDE_LENGTH * 8 > SCREEN_HEIGHT:
    raise ValueError("SCREEN_WIDTH and SCREEN_HEIGHT must be greater than or equal to SQUARE_SIDE_LENGTH * 8")

MOVE_HIGHLIGHT_COLOUR = "green"
CHECK_HIGHLIGHT_COLOUR = "red"


class HighlightType(Enum):
    MOVE = 0
    CHECK = 1


class Highlight:
    def __init__(self, col_indx: ColumnIndex, row_indx: RowIndex, type_: HighlightType) -> None:
        self.col_indx = col_indx
        self.row_indx = row_indx
        self.type = type_

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, tuple):
            return (self.col_indx, self.row_indx) == other
        raise NotImplementedError(f"Cannot compare Highlight with type {type(other).__class__.__name__!r}")


def display_board(screen: pygame.surface.Surface, board: Board, to_highlight: list[Highlight]) -> None:
    for row_indx, row in enumerate(board.squares):
        for col_indx, piece in enumerate(row):
            square_colour = "white" if (row_indx + col_indx) % 2 == 0 else "black"

            try:
                highlight_indx = to_highlight.index((col_indx, row_indx))  #  type: ignore
            except ValueError:
                # No highlight for this square
                has_highlight = False
            else:
                has_highlight = True
                highlight = to_highlight[highlight_indx]
                square_colour = (
                    CHECK_HIGHLIGHT_COLOUR if highlight.type == HighlightType.CHECK else MOVE_HIGHLIGHT_COLOUR
                )

            pygame.draw.rect(
                screen,
                square_colour,
                (
                    col_indx * SQUARE_SIDE_LENGTH + 4 * has_highlight,
                    (7 - row_indx) * SQUARE_SIDE_LENGTH + 4 * has_highlight,
                    SQUARE_SIDE_LENGTH - 8 * has_highlight,
                    SQUARE_SIDE_LENGTH - 8 * has_highlight,
                ),
            )

            if piece is not None:
                piece_name = piece.name
                piece_colour = piece.colour
                piece_image = pygame.image.load(f"src/gui/assets/{piece_colour}/{piece_name}.png")
                if (piece_image.get_width(), piece_image.get_height()) != (
                    SQUARE_SIDE_LENGTH / 2,
                    SQUARE_SIDE_LENGTH / 2,
                ):
                    piece_image = pygame.transform.scale(
                        piece_image, (SQUARE_SIDE_LENGTH // 2, SQUARE_SIDE_LENGTH // 2)
                    )
                screen.blit(
                    piece_image,
                    (  # Ensure image is centered in square
                        (SQUARE_SIDE_LENGTH / 4) + col_indx * SQUARE_SIDE_LENGTH,
                        (SQUARE_SIDE_LENGTH / 4) + (7 - row_indx) * SQUARE_SIDE_LENGTH,
                    ),
                )


class Events:
    TURN_STARTED = pygame.event.custom_type()
    TURN_ENDED = pygame.event.custom_type()
    CHECKED = pygame.event.custom_type()
    CHECKMATED = pygame.event.custom_type()
    GAME_OVER = pygame.event.custom_type()
    PIECE_CAPTURED = pygame.event.custom_type()


def main() -> None:
    pygame.init()

    game_over_sound = pygame.mixer.Sound("src/gui/assets/game-over.wav")
    move_sound = pygame.mixer.Sound("src/gui/assets/move.wav")
    capture_sound = pygame.mixer.Sound("src/gui/assets/capture.wav")
    check_sound = pygame.mixer.Sound("src/gui/assets/check.wav")
    pawn_promotion_sound = pygame.mixer.Sound("src/gui/assets/promote.wav")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Chess")

    # game = Game(board_fen="3qkb2/3pp3/8/6Q1/8/8/8/4K3 b - - 0 1")  # Check or Checkmate
    # game = Game(board_fen="4k3/8/8/8/8/8/2q5/1K6 w - - 0 1")  # Insufficient material
    # game = Game(board_fen="6k1/8/7Q/8/5R2/8/8/3K4 w - - 0 1")  # Stalemate
    # game = Game(board_fen="rnb2bnr/pppPkppp/4p3/3p4/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1")  # Pawn promotion
    # game = Game(board_fen="4kb2/8/8/8/8/8/8/R3K2R w KQ - 0 1")  # Castling
    # game = Game(board_fen="1k3q2/8/8/8/8/8/8/K6Q w - - 49 1")  # 50 move rule
    # game = Game(STARTING_BOARD_FEN.replace("w", "b"))  # Normal game but black starts
    # game = Game()  # Random game
    game = Game(STARTING_BOARD_FEN)  # Normal game

    pygame.event.post(pygame.event.Event(Events.TURN_STARTED))

    to_highlight: list[Highlight] = []
    first_piece_clicked: Piece | None = None
    moves_for_first_piece_clicked: list[Move] = []

    running: bool = True
    while running:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == Events.GAME_OVER:
                    game_over_sound.play()
                    print("\n".join(game.fens))
                    continue

                if event.type == Events.TURN_STARTED:
                    pygame.display.set_caption(f"Chess - {game.board.turn.capitalize()}'s turn")
                    display_board(screen, game.board, to_highlight)

                if event.type in {Events.CHECKMATED, Events.CHECKED}:
                    checked_or_checkmated_king = (
                        game.board.white_pieces if game.board.turn == "WHITE" else game.board.black_pieces
                    ).king
                    checked_or_checkmated_king.can_castle = False
                    to_highlight = [
                        Highlight(
                            checked_or_checkmated_king.col_indx,
                            checked_or_checkmated_king.row_indx,
                            HighlightType.CHECK,
                        )
                    ]

                    if event.type == Events.CHECKMATED:
                        pygame.event.post(pygame.event.Event(Events.GAME_OVER))
                    else:
                        check_sound.play()
                    continue

                if event.type == Events.PIECE_CAPTURED:
                    capture_sound.play()
                    continue

                if event.type == Events.TURN_ENDED:
                    if game.over:
                        display_board(screen, game.board, to_highlight)
                        break

                    first_piece_clicked = None
                    moves_for_first_piece_clicked = []

                    # Have finished ending current turn, so trigger next turn
                    pygame.event.post(pygame.event.Event(Events.TURN_STARTED))
                    continue

                if not game.over and event.type == pygame.MOUSEBUTTONDOWN:
                    col_indx: int = event.pos[0] // SQUARE_SIDE_LENGTH
                    row_indx: int = 7 - (
                        event.pos[1] // SQUARE_SIDE_LENGTH
                    )  # Substract from 7 so that bottom row (white) is row_indx 0, not 7

                    if first_piece_clicked is not None:
                        if col_indx == first_piece_clicked.col_indx and row_indx == first_piece_clicked.row_indx:
                            # Clicked on the same piece, so ignore
                            continue
                        for move in moves_for_first_piece_clicked:
                            # NB: We check not only if the move ends at the clicked square but also
                            # if it starts at the clicked square, since when castling you click the
                            # square of the piece you're castling with, not the square your piece moves to.
                            if move.ends_at(col_indx, row_indx) or move.starts_at(col_indx, row_indx):
                                draw_reason = game.perform_move(move)

                                if not move.captures_piece or move.promotes_pawn:
                                    move_sound.play()

                                if move.captures_piece:
                                    pygame.event.post(pygame.event.Event(Events.PIECE_CAPTURED))

                                if move.promotes_pawn:
                                    capture_sound.stop()
                                    pawn_promotion_sound.play()

                                to_highlight = []
                                moves_for_first_piece_clicked = []

                                if draw_reason is not None:
                                    pygame.display.set_caption(f"Chess - Draw ({draw_reason.value})!")
                                    pygame.event.post(pygame.event.Event(Events.GAME_OVER))
                                elif move.checkmates_enemy:
                                    winner = "white" if game.board.turn == "BLACK" else "black"
                                    pygame.display.set_caption(f"Chess - {winner} wins!")
                                    pygame.event.post(pygame.event.Event(Events.CHECKMATED))
                                elif move.checks_enemy:
                                    pygame.event.post(pygame.event.Event(Events.CHECKED))

                                pygame.event.post(pygame.event.Event(Events.TURN_ENDED))
                                break
                        else:
                            # Not a valid move, so reset move info
                            first_piece_clicked = None
                            to_highlight = [
                                *filter(
                                    # Remove move highlights
                                    lambda highlight: highlight.type != HighlightType.MOVE,
                                    to_highlight,
                                )
                            ]
                            moves_for_first_piece_clicked = []

                            display_board(screen, game.board, to_highlight)

                    if (piece_at_square := game.board.squares[row_indx][col_indx]) is not None:
                        if piece_at_square.colour != game.board.turn:
                            continue

                        if first_piece_clicked is None:
                            first_piece_clicked = piece_at_square

                            for move in piece_at_square.generate_possible_moves(game.board):
                                if not (0 < len(move.components) < 3):
                                    raise ValueError(
                                        f"Expected move to have 1-2 components, but got {len(move.components)}: {move}"
                                    )

                                if len(move.components) == 1:
                                    move_component = move.components[0]
                                    to_highlight.append(
                                        Highlight(
                                            move_component.after.col_indx,
                                            move_component.after.row_indx,
                                            HighlightType.MOVE,
                                        )
                                    )
                                else:
                                    if move.components[0].before == first_piece_clicked:
                                        other_piece = move.components[1].before
                                    else:
                                        other_piece = move.components[0].before
                                    to_highlight.append(
                                        Highlight(other_piece.col_indx, other_piece.row_indx, HighlightType.MOVE)
                                    )
                                moves_for_first_piece_clicked.append(move)

                            display_board(screen, game.board, to_highlight)

            pygame.display.flip()
        except Exception as e:
            print("Error", e, "\nBoard\n", game.board, "Prev Move", game.board.prev_move)

        if not running:
            pygame.quit()


if __name__ == "__main__":
    main()

"""
Sample Game:

[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "1-0"]

1. e3 e6 2. Nc3 e5 3. d4 a5 4. Nb5 Bb4+ 5. c3 Bf8 6. dxe5 Nc6 7. f4 d6 8. b3
Qh4+ 9. g3 Qh6 10. Nxc7+ Kd7 11. Nxa8 d5 12. b4 axb4 13. cxb4 Bxb4+ 14. Kf2 d4
15. exd4 Nxd4 16. Qxd4+ Ke7 17. a3 Ba5 18. Nc7 g5 19. Nd5+ Kd8 20. Nb6+ Kc7 21.
Na8+ Kb8 22. Rb1 Ne7 23. Bg2 Nf5 24. Rxb7+ Kxa8 25. Qa7# 1-0
"""
