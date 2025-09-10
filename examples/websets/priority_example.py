"""
Example demonstrating how to use priority headers with Websets API.

This example shows how to create websets and searches with different priority levels.
Priority can be set to 'low', 'medium', or 'high' to control processing priority.
"""

import os
from exa_py import Exa
from exa_py.websets.types import WebsetSearchBehavior

# Get your API key from environment variable
api_key = os.environ.get("EXA_API_KEY")
exa = Exa(api_key=api_key)

# Create a webset with low priority
print("Creating webset with low priority...")
webset = exa.websets.create(
    {
        "search": {
            "query": "software person in SF",
            "count": 15,
        },
    },
    options={"priority": "low"}  # Simple priority setting
)
print(f"Created webset: {webset.id}")

# Create a search with high priority
print("\nCreating search with high priority...")
search = exa.websets.searches.create(
    webset.id,
    {
        "query": "software people in sf",
        "count": 5,
        "behavior": WebsetSearchBehavior.override.value,
    },
    options={"priority": "high"}  # Simple priority setting
)
print(f"Created search: {search.id}")
