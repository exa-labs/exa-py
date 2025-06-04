from exa_py import Exa
import os
import time

from exa_py.websets.types import CreateWebsetParameters, CreateEnrichmentParameters, CreateWebhookParameters, EventType

# Initialize the client with the provided API key
exa = Exa(os.environ.get("EXA_API_KEY"))

print("Setting up webhooks for real-time updates...")

# Create a webhook to track various webset events
# In a real application, provide your own server URL that can receive webhook callbacks
webhook = exa.websets.webhooks.create(
    params=CreateWebhookParameters(
        events=[
            EventType.webset_created,
            EventType.webset_idle, 
            EventType.webset_item_created,
            EventType.webset_search_completed
        ],
        url="https://webhook.site/"  # Replace with your actual webhook endpoint
    )
)

print(f"Webhook created with ID: {webhook.id}")
print(f"Secret for signature verification: {webhook.secret}")
print(f"Webhook will be triggered for events: {[e for e in webhook.events]}")

# Create a webset that will trigger webhook notifications
webset = exa.websets.create(
    params=CreateWebsetParameters(
        search={
            "query": "AI startups in Boston with funding in the last 2 years",
            "count": 5,
        },
        enrichments=[
            CreateEnrichmentParameters(
                description="Recent funding rounds and amounts",
                format="text",
            ),
        ],
    )
)

print(f"\nWebset created with ID: {webset.id}")
print("Processing has started. Webhooks will be triggered as events occur.")

# In a real application, your webhook endpoint would receive callbacks
# Here we'll wait a bit and then query for webhook attempts to simulate what happened
time.sleep(5)  # Give it some time to process

# List webhook attempts - in a real application, these would be delivered to your webhook URL
try:
    print("\nListing recent webhook attempts:")
    attempts = exa.websets.webhooks.attempts.list(webhook_id=webhook.id, limit=10)
    
    if not attempts.data:
        print("  No webhook attempts found yet. It might take some time for events to be generated.")
    else:
        for attempt in attempts.data:
            print(f"  - Event: {attempt.event_type.value}")
            print(f"    Time: {attempt.attempted_at}")
            print(f"    Success: {attempt.successful}")
            print(f"    Status code: {attempt.response_status_code}")
            print()
except Exception as e:
    print(f"Could not fetch webhook attempts: {e}")

# Wait for webset to complete (this would normally happen asynchronously via webhooks)
print("\nWaiting for webset to complete...")
completed_webset = exa.websets.wait_until_idle(webset.id)
print("Webset processing complete!")

# Check for webhook attempts again after completion
try:
    print("\nListing webhook attempts after completion:")
    attempts = exa.websets.webhooks.attempts.list(webhook_id=webhook.id, limit=10)
    
    if not attempts.data:
        print("  No webhook attempts found. Please check your webhook endpoint configuration.")
    else:
        for attempt in attempts.data:
            print(f"  - Event: {attempt.event_type.value}")
            print(f"    Time: {attempt.attempted_at}")
            print(f"    Success: {attempt.successful}")
            print()
except Exception as e:
    print(f"Could not fetch webhook attempts: {e}")

# Get the items that were found
items = exa.websets.items.list(webset_id=webset.id)
print(f"\nFound {len(items.data)} companies matching the criteria.")

# Cleanup
print("\nCleaning up webhook...")
exa.websets.webhooks.delete(id=webhook.id)
print("Webhook deleted successfully.")

print("\nCleaning up webset...")
exa.websets.delete(id=webset.id)
print("Webset deleted successfully.")
