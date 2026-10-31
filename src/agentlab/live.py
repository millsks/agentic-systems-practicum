"""Connect to the real Claude API when the ``anthropic`` package is installed."""

import importlib
from typing import Any


class LiveModelUnavailableError(RuntimeError):
    """The real API client cannot be created here."""


def get_client(**options: Any) -> Any:
    """Return a real ``anthropic.Anthropic`` client.

    The client resolves credentials from the environment (``ANTHROPIC_API_KEY``, or a profile from
    ``ant auth login``). Never hard-code an API key in code or in a lesson cell.

    Args:
        **options: Passed through to ``anthropic.Anthropic``, such as ``max_retries``.

    Returns:
        The client. Its ``messages.create`` takes the same arguments as ``MockClient``'s.

    Raises:
        LiveModelUnavailableError: The ``anthropic`` package is not installed, as in the browser.
    """
    try:
        anthropic = importlib.import_module("anthropic")
    except ImportError as exc:
        raise LiveModelUnavailableError(
            "The anthropic package is not installed here (it never is in the browser). Run live labs locally with Pixi."
        ) from exc
    return anthropic.Anthropic(**options)
