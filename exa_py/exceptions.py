"""Custom exceptions for the Exa SDK.

This module provides a hierarchy of exceptions for better error handling:

    ExaError (base)
    ├── ExaAPIError (HTTP/API errors)
    │   ├── ExaAuthenticationError (401/403)
    │   ├── ExaRateLimitError (429)
    │   ├── ExaNotFoundError (404)
    │   └── ExaServerError (5xx)
    ├── ExaValidationError (invalid parameters)
    ├── ExaTimeoutError (request/operation timeout)
    └── ExaNetworkError (connection issues)

Example usage:
    from exa_py import Exa
    from exa_py.exceptions import ExaRateLimitError, ExaAuthenticationError

    exa = Exa()
    try:
        results = exa.search("AI news")
    except ExaAuthenticationError:
        print("Invalid API key")
    except ExaRateLimitError as e:
        print(f"Rate limited. Retry after {e.retry_after} seconds")
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ExaError(Exception):
    """Base exception for all Exa SDK errors.

    All exceptions raised by the Exa SDK inherit from this class,
    making it easy to catch any SDK-related error.

    Example:
        try:
            results = exa.search("query")
        except ExaError as e:
            print(f"Exa error: {e}")
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ExaAPIError(ExaError):
    """Exception raised when the Exa API returns an error response.

    Attributes:
        status_code: HTTP status code from the API response.
        message: Error message describing what went wrong.
        response: Raw response body from the API (if available).
        request_id: Request ID for debugging (if available in headers).

    Example:
        try:
            results = exa.search("query")
        except ExaAPIError as e:
            print(f"API error {e.status_code}: {e.message}")
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        response: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self.status_code = status_code
        self.response = response
        self.request_id = request_id

        # Build detailed error message
        detail = f"[{status_code}] {message}"
        if request_id:
            detail += f" (request_id: {request_id})"

        super().__init__(detail)


class ExaAuthenticationError(ExaAPIError):
    """Exception raised when authentication fails (401/403).

    This typically means:
    - The API key is invalid or expired
    - The API key doesn't have permission for the requested operation

    Example:
        try:
            results = exa.search("query")
        except ExaAuthenticationError:
            print("Please check your API key")
    """
    pass


class ExaRateLimitError(ExaAPIError):
    """Exception raised when rate limit is exceeded (429).

    Attributes:
        retry_after: Number of seconds to wait before retrying (if provided by API).

    Example:
        try:
            results = exa.search("query")
        except ExaRateLimitError as e:
            if e.retry_after:
                time.sleep(e.retry_after)
                # Retry the request
    """

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, status_code, response, request_id)
        self.retry_after = retry_after


class ExaNotFoundError(ExaAPIError):
    """Exception raised when a requested resource is not found (404).

    Example:
        try:
            contents = exa.get_contents(["invalid-url"])
        except ExaNotFoundError:
            print("Resource not found")
    """
    pass


class ExaServerError(ExaAPIError):
    """Exception raised when the server encounters an error (5xx).

    These errors are typically transient and can be retried.
    The SDK will automatically retry these errors if retry is enabled.

    Example:
        try:
            results = exa.search("query")
        except ExaServerError:
            print("Server error - please try again later")
    """
    pass


class ExaValidationError(ExaError):
    """Exception raised when invalid parameters are provided.

    This is raised before making an API request when the SDK
    detects invalid input parameters.

    Attributes:
        param: Name of the invalid parameter (if applicable).
        value: The invalid value that was provided (if applicable).

    Example:
        try:
            results = exa.search("query", num_results=-1)
        except ExaValidationError as e:
            print(f"Invalid parameter: {e.param}")
    """

    def __init__(
        self,
        message: str,
        param: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        self.param = param
        self.value = value
        super().__init__(message)


class ExaTimeoutError(ExaError):
    """Exception raised when a request or operation times out.

    This can occur when:
    - The HTTP request exceeds the configured timeout
    - A polling operation (e.g., research task) exceeds max wait time

    Attributes:
        timeout: The timeout value that was exceeded (in seconds).

    Example:
        try:
            results = exa.search("query")
        except ExaTimeoutError as e:
            print(f"Request timed out after {e.timeout}s")
    """

    def __init__(self, message: str, timeout: Optional[float] = None):
        self.timeout = timeout
        super().__init__(message)


class ExaNetworkError(ExaError):
    """Exception raised when a network error occurs.

    This includes:
    - Connection refused
    - DNS resolution failure
    - SSL/TLS errors
    - Connection reset

    Example:
        try:
            results = exa.search("query")
        except ExaNetworkError:
            print("Network error - check your connection")
    """
    pass


# Helper function to create appropriate exception from status code
def exception_from_status_code(
    status_code: int,
    message: str,
    response: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    retry_after: Optional[int] = None,
) -> ExaAPIError:
    """Create the appropriate exception type based on HTTP status code.

    Args:
        status_code: HTTP status code from the response.
        message: Error message.
        response: Raw response body (optional).
        request_id: Request ID from headers (optional).
        retry_after: Retry-After header value for 429 responses (optional).

    Returns:
        An appropriate ExaAPIError subclass instance.
    """
    if status_code == 401 or status_code == 403:
        return ExaAuthenticationError(message, status_code, response, request_id)
    elif status_code == 404:
        return ExaNotFoundError(message, status_code, response, request_id)
    elif status_code == 429:
        return ExaRateLimitError(message, status_code, response, request_id, retry_after)
    elif status_code >= 500:
        return ExaServerError(message, status_code, response, request_id)
    else:
        return ExaAPIError(message, status_code, response, request_id)
