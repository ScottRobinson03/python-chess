if __name__ == "__main__":
    from datetime import datetime
    from tests import test_piece

    test_categories = [
        test_piece.test_init,
        test_piece.test_properties,
        test_piece.test_move_generation,
    ]
    start = datetime.now()

    num_tests = 0
    for test_category in test_categories:
        num_tests += 1
        test_category()

    print(f"Took {(datetime.now() - start).total_seconds()}s to run {num_tests} test categories.")
