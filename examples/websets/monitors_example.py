"""
Basic Monitors Example

This example shows how to use Monitors to automatically keep your Websets 
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
    # Define search parameters that we'll use for both the initial webset and monitor
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
    
    # Create a Monitor using the same search parameters to keep finding new companies
    print("\nCreating monitor...")
    # Cron format: "minute hour day_of_month month day_of_week"
    # Examples:
    # "0 9 * * 1" = Every Monday at 9:00 AM
    # "0 14 * * *" = Every day at 2:00 PM  
    # "0 9 1 * *" = First day of every month at 9:00 AM
    monitor = exa.websets.monitors.create({
        "websetId": webset.id,
        "cadence": {
            "cron": "0 9 * * 1",  # Every Monday at 9:00 AM (weekly)
            "timezone": "America/New_York"
        },
        "behavior": {
            "type": "search",
            "config": {
                "behavior": "append",  # Add new items to the webset
                **search_params,  # Use the same search parameters
            }
        }
    })
    
    print(f"✓ Created monitor: {monitor.id}")
    print(f"  Status: {monitor.status}")
    print(f"  Next run: {monitor.next_run_at}")
    
    # List all monitors for the webset
    print(f"\nMonitors for webset {webset.id}:")
    monitors = exa.websets.monitors.list(webset_id=webset.id)
    for m in monitors.data:
        print(f"  - {m.id}: {m.behavior.type} monitor ({m.status})")

if __name__ == "__main__":
    main() 