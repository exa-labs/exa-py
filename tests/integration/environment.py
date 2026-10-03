"""Client settings the integration tests read from the environment."""

import os
from typing import Optional, Tuple


def client_args(api_key: Optional[str] = None) -> Tuple[Optional[str], ...]:
    """Positional constructor arguments for ``Exa`` and ``AsyncExa``.

    Both clients take the API key first and the base URL second (the keyword
    names differ), so the base URL is passed positionally. It is included only
    when ``EXA_BASE_URL`` is set, leaving the client default otherwise. A
    ``None`` key makes the client read ``EXA_API_KEY`` itself.
    """
    base_url = os.getenv("EXA_BASE_URL")
    return (api_key, base_url) if base_url else (api_key,)
