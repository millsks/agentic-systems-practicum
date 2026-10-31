"""Exceptions named and shaped like the Anthropic Python SDK's, plus mock-only script errors."""


class APIError(Exception):
    """Base class for every error the client raises.

    Attributes:
        message: Human-readable description.
    """

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: Human-readable description.
        """
        super().__init__(message)
        self.message = message


class APIConnectionError(APIError):
    """The request never reached the API (network failure, timeout)."""


class APIStatusError(APIError):
    """The API answered with an error status code.

    Attributes:
        status_code: HTTP status code.
    """

    status_code = 0

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        """Create the error.

        Args:
            message: Human-readable description.
            status_code: Override the class's default status code.
        """
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(APIStatusError):
    """400: the request is malformed; retrying it unchanged will fail again."""

    status_code = 400


class AuthenticationError(APIStatusError):
    """401: the API key is missing or invalid."""

    status_code = 401


class NotFoundError(APIStatusError):
    """404: unknown model or endpoint."""

    status_code = 404


class RateLimitError(APIStatusError):
    """429: too many requests; wait and retry.

    Attributes:
        retry_after: Seconds the server asked you to wait.
    """

    status_code = 429

    def __init__(self, message: str = "rate limit exceeded", *, retry_after: float = 1.0) -> None:
        """Create the error.

        Args:
            message: Human-readable description.
            retry_after: Seconds the server asked you to wait.
        """
        super().__init__(message)
        self.retry_after = retry_after


class InternalServerError(APIStatusError):
    """500 or above: a transient server failure; retrying usually works."""

    status_code = 500


class OverloadedError(APIStatusError):
    """529: the API is temporarily overloaded; retry with backoff."""

    status_code = 529


class MockScriptError(Exception):
    """The mock's script is wrong or used up; a bug in the exercise, not in your agent."""
