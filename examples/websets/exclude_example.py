"""
Exclude Example

Shows how to exclude existing websets when searching to avoid duplicates.
"""

import os
from exa_py import Exa
from exa_py.websets.types import (
    CreateWebsetParameters,
    ExcludeItem,
    ImportSource
)

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    print("Please set EXA_API_KEY environment variable")
    exit(1)

exa = Exa(api_key)

def main():
    query = "AI companies based in SF building foundational models"
    
    try:
        # Create initial webset
        print("Creating initial webset...")
        webset1 = exa.websets.create(
            params=CreateWebsetParameters(
                search={"query": query, "count": 3}
            )
        )
        exa.websets.wait_until_idle(webset1.id)
        
        items1 = exa.websets.items.list(webset_id=webset1.id)
        print(f"Found {len(items1.data)} companies")
        
        # Create new webset excluding the first one
        print("Creating second webset (excluding first)...")
        webset2 = exa.websets.create(
            params=CreateWebsetParameters(
                search={
                    "query": query,
                    "count": 5,
                    "exclude": [ExcludeItem(source=ImportSource.webset, id=webset1.id)]
                }
            )
        )
        exa.websets.wait_until_idle(webset2.id)
        
        items2 = exa.websets.items.list(webset_id=webset2.id)
        print(f"Found {len(items2.data)} new companies (excluded duplicates)")
        
        # Clean up
        exa.websets.delete(webset1.id)
        exa.websets.delete(webset2.id)
        print("Cleanup complete")
        
    except ValueError as e:
        if "Invalid API key" in str(e) or "x-api-key header is invalid" in str(e):
            print("Invalid API key. Get one from https://dashboard.exa.ai")
        else:
            raise e

if __name__ == "__main__":
    main() 