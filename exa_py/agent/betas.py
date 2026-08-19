"""Shared Exa-Beta header construction for the agent API surfaces."""

from __future__ import annotations

from typing import Dict, Optional, Sequence


def headers_for_betas(betas: Optional[Sequence[str]]) -> Optional[Dict[str, str]]:
    """Build the Exa-Beta header from beta identifiers; None when there are none."""
    if not betas:
        return None

    beta_values = [beta for beta in betas if beta]
    if not beta_values:
        return None

    return {"Exa-Beta": ",".join(beta_values)}
