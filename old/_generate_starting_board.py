from src.backend.piece import Piece
from src.typings import BoardList, Colour, PieceName


class Board:
    _black_pieces: list[Piece]
    _white_pieces: list[Piece]

    def _generate_starting_board(self) -> BoardList:
        board: BoardList = []
        for row_indx in range(8):
            inner: list[Piece | None] = []
            for col_indx in range(8):
                if 2 <= row_indx <= 5:
                    inner.append(None)
                    continue

                colour: Colour = "WHITE" if row_indx < 2 else "BLACK"
                piece_name: PieceName = "p" if row_indx in {1, 6} else "rnbqkbnr"[col_indx]  # type: ignore -- Python doesn't narrow the indexing

                if colour == "WHITE":
                    piece = Piece(piece_name.upper(), col_indx, row_indx)  # type: ignore -- Python doesn't like the .upper()
                    self._white_pieces.append(piece)
                else:
                    piece = Piece(piece_name, col_indx, row_indx)
                    self._black_pieces.append(piece)

                inner.append(piece)

            board.append(inner)
        return board
