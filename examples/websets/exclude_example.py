"""
Exclude Example

This example shows how to exclude existing websets and imports when creating
a new webset to avoid finding duplicate results.
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
    print("Example: export EXA_API_KEY='your-api-key-here'")
    exit(1)

exa = Exa(api_key)

def main():
    # First, create a webset with some AI companies
    print("Creating initial webset with AI companies...")
    known_companies_webset = exa.websets.create(
        params=CreateWebsetParameters(
            search={
                "query": "AI companies based in SF building foundational models",
                "count": 3
            }
        )
    )
    
    print(f"✓ Created known companies webset: {known_companies_webset.id}")
    print("Waiting for webset to complete...")
    exa.websets.wait_until_idle(known_companies_webset.id)
    
    # Get the companies we found
    known_items = exa.websets.items.list(webset_id=known_companies_webset.id)
    print(f"\nKnown companies ({len(known_items.data)} found):")
    for i, item in enumerate(known_items.data, 1):
        print(f"  {i}. {item.properties.url} - {item.properties.description}")
    
    # Create a new webset with the same query but exclude the known companies
    print(f"\nCreating new webset with same query but excluding known companies...")
    new_webset = exa.websets.create(
        params=CreateWebsetParameters(
            search={
                "query": "AI companies based in SF building foundational models",  # Same query!
                "count": 5,
                "exclude": [
                    ExcludeItem(
                        source=ImportSource.webset,
                        id=known_companies_webset.id
                    )
                ]
            }
        )
    )
    
    print(f"✓ Created new webset: {new_webset.id}")
    print("Waiting for new webset to complete...")
    exa.websets.wait_until_idle(new_webset.id)
    
    # Get the new results (should not include the excluded companies)
    new_items = exa.websets.items.list(webset_id=new_webset.id)
    print(f"\nNew companies found ({len(new_items.data)} total):")
    for i, item in enumerate(new_items.data, 1):
        print(f"  {i}. {item.properties.url} - {item.properties.description}")
    
    print(f"\n✓ Successfully excluded {len(known_items.data)} known companies from search")
    
    # Clean up
    print("\nCleaning up...")
    exa.websets.delete(known_companies_webset.id)
    exa.websets.delete(new_webset.id)
    print("✓ Cleaned up successfully")

if __name__ == "__main__":
    main() 