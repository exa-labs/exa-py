"""Example of listing and managing multiple research requests."""

import os
from exa_py import Exa

# Initialize the client
api_key = os.environ.get("EXA_API_KEY")
base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
client = Exa(api_key=api_key, base_url=base_url)

# Create multiple research requests
print("Creating multiple research requests...")
research_ids = []

topics = [
    "What is Python best used for?",
    "Name the largest ocean on Earth.",
    "What year was the internet invented?",
]

for topic in topics:
    research = client.research.create(instructions=topic, model="exa-research")
    research_ids.append(research.research_id)
    print(f"  Created research {research.research_id[:8]}... for: {topic[:50]}...")

print(f"\nCreated {len(research_ids)} research requests")

# List all research requests
print("\nListing research requests (first page)...")
list_response = client.research.list(limit=10)

print(f"Found {len(list_response.data)} research requests")
print(f"Has more: {list_response.has_more}")
if list_response.next_cursor:
    print(f"Next cursor: {list_response.next_cursor[:20]}...")

# Display research status
print("\nResearch Status Summary:")
for research in list_response.data:
    status_symbol = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "canceled": "⏹️",
    }.get(research.status, "❓")

    print(f"{status_symbol} {research.research_id[:8]}... - {research.status}")
    print(f"   Created: {research.created_at}")
    print(f"   Model: {research.model}")
    print(f"   Instructions: {research.instructions[:80]}...")

    if research.status == "completed":
        print(f"   Cost: ${research.cost_dollars.total:.4f}")
    elif research.status == "failed" and hasattr(research, "error"):
        print(f"   Error: {research.error}")
    print()

# Paginate through results if there are more
if list_response.has_more and list_response.next_cursor:
    print("\nFetching next page...")
    next_page = client.research.list(cursor=list_response.next_cursor, limit=10)
    print(f"Found {len(next_page.data)} more research requests on page 2")

# Get details of a specific research with events
if research_ids:
    print(f"\nGetting detailed info for research {research_ids[0][:8]}...")
    detailed = client.research.get(research_ids[0], events=True)

    print(f"Status: {detailed.status}")
    if detailed.events:
        print(f"Number of events: {len(detailed.events)}")

        # Count event types
        event_counts = {}
        for event in detailed.events:
            event_type = event.event_type
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        print("Event breakdown:")
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")

# Wait for all to complete (with timeout)
print(f"\nWaiting for {len(research_ids)} research requests to complete...")
completed_count = 0
failed_count = 0

for research_id in research_ids:
    try:
        result = client.research.poll_until_finished(
            research_id,
            poll_interval=2000,
            timeout_ms=180000,  # 3 minutes per research
        )
        if result.status == "completed":
            completed_count += 1
            print(
                f"✅ {research_id[:8]}... completed (${result.cost_dollars.total:.4f})"
            )
        elif result.status == "failed":
            failed_count += 1
            print(f"❌ {research_id[:8]}... failed")
    except TimeoutError:
        print(f"⏱️ {research_id[:8]}... timed out")

print(f"\nSummary: {completed_count} completed, {failed_count} failed")

# List again to see updated statuses
print("\nFinal status check:")
final_list = client.research.list(limit=20)
for research in final_list.data:
    if research.research_id in research_ids:
        print(f"  {research.research_id[:8]}... - {research.status}")
