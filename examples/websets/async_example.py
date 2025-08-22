"""
Async Websets example demonstrating basic usage of the async websets client.
"""
import asyncio
import os
from exa_py import AsyncExa
from exa_py.websets.types import CreateWebsetParameters, CreateEnrichmentParameters


async def main():
    # Initialize the async Exa client
    exa_api_key = os.environ.get("EXA_API_KEY")
    if not exa_api_key:
        raise ValueError("EXA_API_KEY environment variable not set!")
    
    async_exa = AsyncExa(exa_api_key)
    
    try:
        # Create a new webset
        print("Creating a new webset...")
        webset = await async_exa.websets.create(
            params=CreateWebsetParameters(
                search={
                    "query": "Tech companies in the United States with more than 20 and less than 100 employees",
                    "count": 10,
                },
                enrichments=[
                    CreateEnrichmentParameters(
                        description="LinkedIn profile URL of VP of Engineering or related role",
                        format="text",
                    ),
                ],
            )
        )
        print(f"Created webset: {webset.id}")
        
        # List websets
        print("\nListing websets...")
        websets_response = await async_exa.websets.list(limit=5)
        print(f"Found {len(websets_response.data)} websets")
        
        # Get webset details
        print(f"\nGetting details for webset {webset.id}...")
        webset_details = await async_exa.websets.get(webset.id)
        print(f"Webset status: {webset_details.status}")
        
        # Wait for webset to be idle
        print(f"\nWaiting for webset to be idle...")
        idle_webset = await async_exa.websets.wait_until_idle(webset.id, timeout=300)
        print(f"Webset is now idle: {idle_webset.status}")
        
        # List items (will be empty for new webset)
        print(f"\nListing items in webset {webset.id}...")
        items_response = await async_exa.websets.items.list(webset.id, limit=10)
        print(f"Found {len(items_response.data)} items")
        
        # Use async generator to list all items (if there were many)
        print(f"\nUsing async generator to iterate through items...")
        item_count = 0
        async for item in async_exa.websets.items.list_all(webset.id, limit=100):
            item_count += 1
            # Break early for demo
            if item_count >= 5:
                break
        print(f"Processed {item_count} items with async generator")
        
        # List events
        print(f"\nListing recent events...")
        events_response = await async_exa.websets.events.list(limit=5)
        print(f"Found {len(events_response.data)} recent events")
        
        # List monitors
        print(f"\nListing monitors...")
        monitors_response = await async_exa.websets.monitors.list(limit=5)
        print(f"Found {len(monitors_response.data)} monitors")
        
        # Clean up - delete the test webset
        print(f"\nDeleting test webset {webset.id}...")
        deleted_webset = await async_exa.websets.delete(webset.id)
        print(f"Deleted webset: {deleted_webset.id}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the async client
        await async_exa.close()


if __name__ == "__main__":
    asyncio.run(main())
