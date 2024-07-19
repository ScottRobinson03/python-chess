from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.backend.piece import Piece

BoardList = list[list["Piece | None"]]

Colour = Literal["BLACK"] | Literal["WHITE"]
PieceName = (
    Literal["P"]  # White Pawn
    | Literal["N"]  # White Knight
    | Literal["B"]  # White Bishop
    | Literal["R"]  # White Rook
    | Literal["Q"]  # White Queen
    | Literal["K"]  # White King
    | Literal["p"]  # Black Pawn
    | Literal["n"]  # Black Knight
    | Literal["b"]  # Black Bishop
    | Literal["r"]  # Black Rook
    | Literal["q"]  # Black Queen
    | Literal["k"]  # Black King
)
FenChar = (
    PieceName
    | Literal["1"]
    | Literal["2"]
    | Literal["3"]
    | Literal["4"]
    | Literal["5"]
    | Literal["6"]
    | Literal["7"]
    | Literal["8"]
)

Column = (
    Literal["a"]
    | Literal["b"]
    | Literal["c"]
    | Literal["d"]
    | Literal["e"]
    | Literal["f"]
    | Literal["g"]
    | Literal["h"]
)
ColumnIndex = int
Row = int  # 1-8
RowIndex = int
Position = str

ChecksEnemy = bool
CheckmatesEnemy = bool
IsStalemate = bool

RawMove = tuple[
    "Piece",  # piece before move
    "Piece",  # piece after move
    "Piece | None",  # piece captured by move
]
