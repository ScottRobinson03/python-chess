from collections.abc import Callable
from typing import Any, Optional, Type

from .errors import (
    ExpectedError,
    InvalidTestSettings,
    UnexpectedError,
    UnexpectedErrorMessage,
    UnexpectedErrorType,
    UnexpectedResponse,
)


def perform_test(
    test_name: str,
    function: Callable,
    *args,
    expected_error: Optional[Type[Exception]] = None,
    expected_error_message: Optional[str] = None,
    expected_response: Any = None,
    expected_response_format: Optional[str] = None,
    ignore_order: bool = False,
    **kwargs,
) -> None:
    """
    Handler for running tests.

    If `expected_error` is set then `expected_error_message` must also be set.
    If `expected_response` is set then `expected_response_format` cannot be, and vice-versa.
    `expected_error` and `expected_error_message` are incompatible with `expected_response`/`expected_response_format`.
    """
    if (expected_error is not None and expected_error_message is None) or (
        expected_error is None and expected_error_message is not None
    ):
        raise InvalidTestSettings(
            test_name, "Either `expected_error` and `expected_error_message` must be set or they must be unset"
        )

    if expected_error:
        if expected_response is not None or expected_response_format is not None:
            raise InvalidTestSettings(
                test_name,
                "`expected_error` and `expected_error_message` cannot be used in "
                "conjunction with `expected_response`/`expected_response_format`",
            )
        perform_test_expecting_error(
            test_name,
            function,
            *args,
            expected_error=expected_error,
            expected_error_message=expected_error_message,  # type: ignore (linting thinks could be `None` but it can't)
            **kwargs,
        )
    else:
        perform_test_not_expecting_error(
            test_name,
            function,
            *args,
            expected_response=expected_response,
            expected_response_format=expected_response_format,
            ignore_order=ignore_order,
            **kwargs,
        )


def perform_test_expecting_error(
    test_name: str, function: Callable, *args, expected_error: Type[Exception], expected_error_message: str, **kwargs
) -> None:
    """
    Run a test that expects an error.

    :param test_name:                   The name of the test we're running
    :param function:                    The function we're testing
    :param args:                        The args to pass to the function we're testing
    :param expected_error:              The expected error class
    :param expected_error_message:      The expected error message
    :param kwargs:                      The kwargs to pass to the function we're testing
    """
    try:
        function(*args, **kwargs)
    except expected_error as e:
        if (actual_error_message := e.args[0]) == expected_error_message:
            print(
                f"Test {test_name!r} passed! Got expected error type ({expected_error.__name__!r}) "
                f"and message ({expected_error_message!r})."
            )
        else:
            raise UnexpectedErrorMessage(test_name, expected_error_message, actual_error_message)
    except Exception as e:
        raise UnexpectedErrorType(test_name, expected_error, type(e), e.args[0])
    else:
        raise ExpectedError(test_name, expected_error)


def perform_test_not_expecting_error(
    test_name: str,
    function: Callable,
    *args,
    expected_response: Optional[Any],
    expected_response_format: Optional[str],
    ignore_order: bool,
    **kwargs,
) -> None:
    """
    Run a test that doesn't expect an error.

    :param test_name:                   The name of the test we're running
    :param function:                    The function we're testing
    :param args:                        The args to pass to the function we're testing
    :param expected_response:           The expected response message (incompatible with `expected_error_message`)
    :param expected_response_format:    The expected response format (incompatible with `expected_response`)
    :param kwargs:                      The kwargs to pass to the function we're testing
    """
    if expected_response is None and expected_response_format is None:
        raise InvalidTestSettings(
            test_name, "Test must have either `expected_response` or `expected_response_format` set"
        )

    if expected_response is not None and expected_response_format is not None:
        raise InvalidTestSettings(
            test_name, "Test cannot have both `expected_response` and `expected_response_format` set"
        )

    try:
        result = function(*args, **kwargs)
    except Exception as e:
        raise UnexpectedError(test_name, type(e), e.args[0])
    else:
        # TODO: Think about how to implement format validation
        #  NB: I *think* it's redundant since converts in the interactions so would error there if not valid format(?)
        if expected_response_format is not None:
            print(f"Skipping test {test_name!r} since it expects a certain format and this hasn't yet been implemented")
            #    if expected_response_format[-2:] == '[]':
            #        if not (validation_function := FORMAT_VALIDATORS.get(expected_response_format[:-2])):
            #            raise InvalidResponseFormat(test_name, expected_response_format[:-2])

            #        for x in result:
            #            try:
            #                if (validation_result := validation_function(x)).get('error'):
            #                    raise InvalidResponse(test_name, expected_response_format[:-2], x, validation_result)
            #            except KeyError as e:
            #                raise InvalidResponse(
            #                    test_name, expected_response_format[:-2], x, {"error": f"KeyError: '{e.args[0]}'"}
            #                )

            #    else:
            #        if not (validation_function := FORMAT_VALIDATORS.get(expected_response_format)):  # not a valid format
            #            raise InvalidResponseFormat(test_name, expected_response_format)

            #        if (validation_result := validation_function(result)).get('error'):
            #            raise InvalidResponse(test_name, expected_response_format, result, validation_result)

            #    print(
            #        f"Test {test_name!r} passed! No unexpected errors occurred "
            #        f"and got the expected response format ({expected_response_format})."
            #    )
            #    return

        # `expected_response_format` isn't provided so check against `expected_response`

        elif (ignore_order and sorted(result) == sorted(expected_response)) or (  # type: ignore
            (not ignore_order) and result == expected_response
        ):
            print(
                f"Test {test_name!r} passed! No unexpected errors occurred "
                f"and got the expected response ({expected_response!r})."
            )
        else:
            raise UnexpectedResponse(
                test_name,
                expected_response,  # noqa (linting thinks could be `None` but can't)
                result,
            )
