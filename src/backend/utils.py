from src.typings import Column, ColumnIndex


STARTING_BOARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def column_index_to_letter(col_indx: int) -> Column:
    return "abcdefgh"[col_indx]  # type: ignore -- Python doesn't narrow subscriptions


def letter_to_column_index(letter: Column) -> ColumnIndex:
    return "abcdefgh".index(letter)
