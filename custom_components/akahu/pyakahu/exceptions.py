"""Errors raised by the Akahu client."""


class AkahuError(Exception):
    """Base error for the Akahu client."""


class AkahuAuthError(AkahuError):
    """Error raised when authentication fails."""


class AkahuConnectionError(AkahuError):
    """Error raised when the API is unreachable."""
