"""Typed errors raised by the Exa SDK.

`ExaTimeoutError` is the one class to catch for a request that exceeded its
timeout, whichever HTTP stack sent it: the sync client uses Requests, the async
client uses HTTPX, and each reports timeouts with its own exception classes.

`typed_timeouts` is the decorator the SDK puts on every function that performs
HTTP I/O, so those transport timeouts surface as `ExaTimeoutError`.
"""

import functools
import inspect
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Type, TypeVar

import httpx
import requests
from urllib3.exceptions import ReadTimeoutError

F = TypeVar("F", bound=Callable[..., Any])


class ExaTimeoutError(Exception):
    """A request to the Exa API exceeded its timeout.

    Raised by `Exa` and `AsyncExa` alike. The raised error is also an instance
    of the exception class the HTTP library raised (for example
    `requests.exceptions.ReadTimeout` or `httpx.ReadTimeout`) and carries the
    same message and attributes, so `except` clauses written against those
    classes keep matching. The original exception is available as `__cause__`.

    The SDK's own calls and stream iterators raise it. A raw streamed response
    returned by `Exa.request` / `AsyncExa.async_request` is read by the caller,
    so a timeout there raises the HTTP library's exception as is.

    Examples:
        >>> try:
        ...     exa.search("latest AI developments", timeout=5)
        ... except ExaTimeoutError:
        ...     print("The search timed out.")
    """


# One typed class per transport exception class, created on first use.
_TYPED_CLASSES: Dict[Type[BaseException], Type[BaseException]] = {}


def _is_timeout(error: BaseException) -> bool:
    """Whether a transport exception reports an elapsed timeout."""
    if isinstance(error, (requests.exceptions.Timeout, httpx.TimeoutException)):
        return True
    # Requests reports a read timeout hit while iterating a streamed body as a
    # ConnectionError wrapping urllib3's ReadTimeoutError.
    return isinstance(error, requests.exceptions.ConnectionError) and any(
        isinstance(arg, ReadTimeoutError) for arg in error.args
    )


def _typed_class(transport_class: Type[BaseException]) -> Type[BaseException]:
    """Return the class deriving from `ExaTimeoutError` and `transport_class`."""
    typed_class = _TYPED_CLASSES.get(transport_class)
    if typed_class is None:
        typed_class = type(
            ExaTimeoutError.__name__,
            (ExaTimeoutError, transport_class),
            {
                "__module__": ExaTimeoutError.__module__,
                "__doc__": ExaTimeoutError.__doc__,
                # The class is not importable by name, so pickle and copy
                # rebuild an instance from its transport class instead.
                "__reduce__": lambda self: (
                    _build_exa_timeout,
                    (transport_class, self.args, dict(self.__dict__)),
                ),
            },
        )
        _TYPED_CLASSES[transport_class] = typed_class
    return typed_class


def _build_exa_timeout(
    transport_class: Type[BaseException], args: tuple, state: Dict[str, Any]
) -> BaseException:
    """Build the typed timeout for `transport_class` with the given message and attributes.

    Built without calling __init__: the transport classes take different
    constructor arguments, and `args` and `state` are the whole of what an
    exception of that class carries.
    """
    typed_class = _typed_class(transport_class)
    typed = typed_class.__new__(typed_class)
    typed.__dict__.update(state)
    typed.args = args
    return typed


def _as_exa_timeout(error: BaseException) -> BaseException:
    """Return `error` re-typed as an `ExaTimeoutError`.

    The result is an instance of a class deriving from both `ExaTimeoutError`
    and `type(error)`, with the message and attributes of `error`.
    """
    return _build_exa_timeout(type(error), error.args, error.__dict__)


@contextmanager
def _raising_exa_timeouts() -> Iterator[None]:
    """Re-raise a transport timeout from the enclosed block as `ExaTimeoutError`."""
    try:
        yield
    except (requests.exceptions.RequestException, httpx.TransportError) as error:
        if isinstance(error, ExaTimeoutError) or not _is_timeout(error):
            raise
        raise _as_exa_timeout(error) from error


def typed_timeouts(function: F) -> F:
    """Make a function that performs HTTP I/O raise `ExaTimeoutError` on a timeout.

    Works on plain functions, coroutine functions, generator functions and
    async generator functions; for the generators it covers every step of the
    iteration. Any other exception passes through unchanged.
    """
    if inspect.isasyncgenfunction(function):

        @functools.wraps(function)
        async def async_generator_wrapper(*args: Any, **kwargs: Any) -> Any:
            generator = function(*args, **kwargs)
            try:
                with _raising_exa_timeouts():
                    async for item in generator:
                        yield item
            finally:
                await generator.aclose()

        return async_generator_wrapper  # type: ignore[return-value]

    if inspect.iscoroutinefunction(function):

        @functools.wraps(function)
        async def coroutine_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _raising_exa_timeouts():
                return await function(*args, **kwargs)

        return coroutine_wrapper  # type: ignore[return-value]

    if inspect.isgeneratorfunction(function):

        @functools.wraps(function)
        def generator_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _raising_exa_timeouts():
                yield from function(*args, **kwargs)

        return generator_wrapper  # type: ignore[return-value]

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with _raising_exa_timeouts():
            return function(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
