"""Typed errors raised by the Exa SDK.

`ExaTimeoutError` is the one class to catch for a request that exceeded its
timeout, whichever HTTP stack sent it: the sync client uses Requests, the async
client uses HTTPX, and each reports timeouts with its own exception classes.

`typed_timeouts` is the decorator the SDK puts on every function that performs
HTTP I/O, so those transport timeouts surface as `ExaTimeoutError`.
`reporting_failover_connect_timeouts` wraps the sync client's Requests calls
so a connect timeout stays a timeout on a host with several addresses.
"""

import functools
import inspect
import socket
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional, Type, TypeVar

import httpx
import requests
from urllib3.exceptions import NewConnectionError, ReadTimeoutError

F = TypeVar("F", bound=Callable[..., Any])


class ExaTimeoutError(Exception):
    """A request to the Exa API exceeded its timeout.

    Raised by `Exa` and `AsyncExa` alike. The raised error is also an instance
    of the exception class the HTTP library raised (for example
    `requests.exceptions.ReadTimeout` or `httpx.ReadTimeout`) and carries the
    same message and attributes, so `except` clauses written against those
    classes keep matching. The original exception is available as `__cause__`.

    The SDK's own calls raise it. A timeout bounds connecting and each wait
    for data from the server. For a streaming call it bounds the wait for the
    response to start. Once a successful response has started, its stream is
    read with no timeout, so iterating a stream never raises it.

    It is not a `builtins.TimeoutError`, which the polling helpers
    (`wait_until_idle`, `wait_until_completed`, `poll_until_finished`,
    `create_and_wait`) raise when their own deadline passes. Catch both where
    both can happen.

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


# The HTTPX timeout classes, each with the name of the timeout setting it reports.
_HTTPX_TIMEOUT_SETTINGS = (
    (httpx.ConnectTimeout, "connect"),
    (httpx.ReadTimeout, "read"),
    (httpx.WriteTimeout, "write"),
    (httpx.PoolTimeout, "pool"),
)


def _describe_timeout(error: BaseException) -> str:
    """Describe a transport timeout that carries no message of its own.

    HTTPX raises its timeouts with the empty message of the asyncio or AnyIO
    timeout underneath, so the description names the timeout the exception's
    class reports and the limit its request set for it, in the words urllib3
    uses: "Read timed out. (read timeout=5)".
    """
    setting = next(
        (name for cls, name in _HTTPX_TIMEOUT_SETTINGS if isinstance(error, cls)), None
    )
    if setting is None:
        return "Request timed out."
    try:
        limit = error.request.extensions.get("timeout", {}).get(setting)  # type: ignore[attr-defined]
    except RuntimeError:  # HTTPX raises this for an exception built without a request.
        limit = None
    if limit is None:
        return f"{setting.capitalize()} timed out."
    return f"{setting.capitalize()} timed out. ({setting} timeout={limit})"


def _as_exa_timeout(error: BaseException) -> BaseException:
    """Return `error` re-typed as an `ExaTimeoutError`.

    The result is an instance of a class deriving from both `ExaTimeoutError`
    and `type(error)`, with the attributes of `error` and its message, or a
    description of the timeout when `error` has an empty message.
    """
    args = error.args if str(error) else (_describe_timeout(error),)
    return _build_exa_timeout(type(error), args, error.__dict__)


def _connect_timeout_hidden_by_failover(
    error: requests.exceptions.ConnectionError,
    timeout: Optional[float],
    elapsed: float,
) -> Optional[requests.exceptions.ConnectTimeout]:
    """Return the connect timeout `error` hides, or None when it hides none.

    urllib3 connects to the addresses of a host one after another, giving each
    the whole connect timeout, and when every one fails it raises the error of
    the last alone. So when an earlier address timed out and the last refused
    the connection or had no route, Requests raises a plain ConnectionError and
    the timeout is lost. The time the attempt took is the one trace it leaves:
    a connection that failed only once the connect timeout had elapsed timed
    out on an address, and is returned as the ConnectTimeout it was. One that
    failed sooner, such as every address refusing at once, and a failed name
    lookup stay ConnectionErrors. The elapsed time includes the name lookup.
    """
    if timeout is None or elapsed < timeout or not error.args:
        return None
    reason = getattr(error.args[0], "reason", None)
    if not isinstance(reason, NewConnectionError):
        return None
    if isinstance(reason.__cause__ or reason.__context__, socket.gaierror):
        return None
    return requests.exceptions.ConnectTimeout(
        f"Connect timed out. (connect timeout={timeout}) "
        f"The last address tried failed with: {error}",
        request=error.request,
        response=error.response,
    )


@contextmanager
def reporting_failover_connect_timeouts(timeout: Optional[float]) -> Iterator[None]:
    """Raise a connect timeout that urllib3's address failover hid as a ConnectTimeout.

    Wraps the Requests calls of the enclosed block, made with `timeout` as
    their connect timeout. The ConnectTimeout raised is a ConnectionError too,
    so handlers written for the error Requests raised keep matching, and
    `typed_timeouts` turns it into an `ExaTimeoutError`.
    """
    started = time.monotonic()
    try:
        yield
    except requests.exceptions.ConnectionError as error:
        connect_timeout = _connect_timeout_hidden_by_failover(
            error, timeout, time.monotonic() - started
        )
        if connect_timeout is None:
            raise
        raise connect_timeout from error


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
