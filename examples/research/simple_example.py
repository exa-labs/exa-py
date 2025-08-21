"""Simple example of using the Research API without streaming or schemas."""

import os
from exa_py import Exa

# Initialize the client
api_key = os.environ.get("EXA_API_KEY")
base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
client = Exa(api_key=api_key, base_url=base_url)

# Create a simple research request
print("Creating research request...")
research = client.research.create(
    instructions="What is the capital of France and what is it famous for?",
    model="exa-research",
)

print(f"Research created with ID: {research.research_id}")
print(f"Status: {research.status}")

# Poll until the research is complete
print("\nWaiting for research to complete...")
completed_research = client.research.poll_until_finished(
    research.research_id,
    poll_interval=2000,  # Poll every 2 seconds
    timeout_ms=300000,  # 5 minute timeout
)

print("\nResearch completed!")
print(f"Status: {completed_research.status}")

if completed_research.status == "completed":
    print(f"\nOutput:\n{completed_research.output.content}")
    print("\nCost breakdown:")
    print(f"  Total: ${completed_research.cost_dollars.total:.4f}")
    print(f"  Searches: {completed_research.cost_dollars.num_searches}")
    print(f"  Pages: {completed_research.cost_dollars.num_pages}")
    print(f"  Reasoning tokens: {completed_research.cost_dollars.reasoning_tokens}")
elif completed_research.status == "failed":
    print(f"Research failed with error: {completed_research.error}")
