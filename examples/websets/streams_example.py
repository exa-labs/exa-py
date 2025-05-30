"""
Basic Streams Example

This example shows how to use Streams to automatically keep your Websets 
updated with fresh data on a schedule.
"""

import os
from exa_py import Exa
from exa_py.websets.types import CreateWebsetParameters

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    print("Please set EXA_API_KEY environment variable")
    print("Example: export EXA_API_KEY='your-api-key-here'")
    exit(1)

exa = Exa(api_key)

def main():
    # Define search parameters that we'll use for both the initial webset and stream
    search_params = {
        "query": "AI startups that raised Series A funding",
        "count": 10,
        "criteria": [
            {"description": "Company is an AI startup"},
            {"description": "Company has raised Series A funding in the last week"}
        ],
        "entity": {"type": "company"}
    }
    
    # Create a Webset to test our search parameters
    print("Creating webset...")
    webset = exa.websets.create(
        params=CreateWebsetParameters(
            search=search_params
        )
    )
    
    print(f"✓ Created webset: https://websets.exa.ai/{webset.id}")
    
    # Wait for the webset to complete
    print("Waiting for webset to complete...")
    exa.websets.wait_until_idle(webset.id)
    
    # List the items to see what we found
    items_response = exa.websets.items.list(webset_id=webset.id)
    
    print(f"✓ Webset found {len(items_response.data)} items")
    if items_response.data:
        print("Sample results:")
        for item in items_response.data[:3]:  # Show first 3 results
            print(f"  - {item.properties.description}")
    
    # Create a Stream using the same search parameters to keep finding new companies
    print("\nCreating stream...")
    stream = exa.websets.streams.create({
        "websetId": webset.id,
        "cadence": {
            "frequency": "weekly",
            "timezone": "America/New_York", 
            "time": "09:00"
        },
        "behavior": {
            "type": "search",
            "config": {
                "parameters": {
                    **search_params,  # Use the same search parameters
                    "behavior": "append"  # Add new items to the webset
                }
            }
        }
    })
    
    print(f"✓ Created stream: {stream.id}")
    print(f"  Status: {stream.status}")
    print(f"  Next run: {stream.next_run_at}")
    
    # List all streams for the webset
    print(f"\nStreams for webset {webset.id}:")
    streams = exa.websets.streams.list(webset_id=webset.id)
    for s in streams.data:
        print(f"  - {s.id}: {s.behavior.type} stream ({s.status})")

if __name__ == "__main__":
    main() 