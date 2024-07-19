from typing import Any, Type


class TestFailure(Exception):
    """Generic parent class for all test failures."""

    def __init__(self, test_name: str, message: str):
        self.test_name = test_name
        self.message = message
        super().__init__(self, f"Test {test_name!r} failed - {message}.")


class ExpectedError(TestFailure):
    """Raised when the test expected an error, but one wasn't raised."""

    def __init__(self, test_name: str, expected_error: Type[Exception]):
        super().__init__(test_name, f"Expected an error of type {expected_error.__name__!r} but didn't get any error")


class InvalidTestSettings(TestFailure):
    """Raised when a test has invalid configuration (incompatible parameters)."""

    def __init__(self, test_name: str, message: str):
        super().__init__(test_name, message)


class UnexpectedError(TestFailure):
    """Raised when the test didn't expect any errors, but got one."""

    def __init__(self, test_name: str, error_type: Type[Exception], error_message: str):
        super().__init__(
            test_name, f"Got an unexpected error of type {error_type.__name__!r} with error message {error_message!r}"
        )


class UnexpectedErrorMessage(TestFailure):
    """Raised when a test expected an error message, but not the one it got."""

    def __init__(self, test_name: str, expected_message: str, actual_message: str):
        super().__init__(test_name, f"Expected message {expected_message!r} but got {actual_message!r}")


class UnexpectedErrorType(TestFailure):
    """Raised when a test expected an error, but not the one it got."""

    def __init__(
        self, test_name: str, expected_error: Type[Exception], actual_error: Type[Exception], error_message: str
    ):
        super().__init__(
            test_name,
            f"Expected error class {expected_error.__name__!r} but got "
            f"{actual_error.__name__!r} with error message {error_message!r}",
        )


class UnexpectedResponse(TestFailure):
    """Raised when the test expected a response, but not the one it got."""

    def __init__(
        self,
        test_name: str,
        expected_response: Any,
        actual_response: Any,
    ):
        super().__init__(test_name, f"Expected response {expected_response!r} but got {actual_response!r}")


# class InvalidResponseFormat(TestFailure):
#     """Raised when the test has an invalid response format passed to it."""

#     def __init__(self, test_name: str, response_format: str):
#         super().__init__(test_name, f"InvalidResponseFormat: {response_format!r} is not a valid response format")


# class InvalidResponse(TestFailure):
#     """Raised when the test responds with an unexpected format."""

#     def __init__(
#         self,
#         test_name: str,
#         expected_response_format: str,
#         response_value: Union[str, dict, list[dict]],
#         error: Union[dict, bool],
#     ):
#         super().__init__(
#             test_name,
#             f"Expected format of {expected_response_format!r} but the response "
#             f"({response_value!r}) doesn't meet that format. Error from validation function: " + "N/A"
#             if isinstance(error, bool)
#             else repr(error.get("error_description") or error.get("error")),
#         )
