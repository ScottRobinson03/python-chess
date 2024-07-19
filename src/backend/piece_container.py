from dataclasses import dataclass

from src.backend.piece import Piece


@dataclass()
class PieceContainer:
    all: list[Piece]
    king: Piece
    rooks: list[Piece]
