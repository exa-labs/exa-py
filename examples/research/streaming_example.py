"""Example of streaming research events in real-time."""

import os
from exa_py import Exa

# Initialize the client
api_key = os.environ.get("EXA_API_KEY")
base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
client = Exa(api_key=api_key, base_url=base_url)

# Create a research request
print("Creating research request...")
research = client.research.create(
    instructions="List the top 3 programming languages in 2024 and their main use cases.",
    model="exa-research",
)

print(f"Research created with ID: {research.research_id}")
print("\nStreaming events...\n")

# Stream events as they happen
for event in client.research.get(research.research_id, stream=True):
    event_type = event.event_type

    if event_type == "research-definition":
        print(f"[Research Started] ID: {event.research_id}")
        print(f"  Instructions: {event.instructions[:100]}...")

    elif event_type == "plan-definition":
        print(f"[Plan Created] Plan ID: {event.plan_id}")

    elif event_type == "plan-operation":
        if event.data.type == "think":
            print(f"[Plan Thinking] {event.data.content[:100]}...")

    elif event_type == "plan-output":
        if event.output.output_type == "tasks":
            print(
                f"[Plan Output] Creating {len(event.output.tasks_instructions)} tasks"
            )
            for i, instruction in enumerate(event.output.tasks_instructions, 1):
                print(f"  Task {i}: {instruction[:80]}...")
        elif event.output.output_type == "stop":
            print(f"[Plan Complete] {event.output.reasoning[:100]}...")

    elif event_type == "task-definition":
        print(f"[Task Started] Task ID: {event.task_id}")
        print(f"  Instructions: {event.instructions[:100]}...")

    elif event_type == "task-operation":
        if event.data.type == "think":
            print(f"[Task Thinking] {event.data.content[:100]}...")
        elif event.data.type == "search":
            print(f"[Task Search] Query: {event.data.query}")
            print(f"  Found {len(event.data.results)} results")
        elif event.data.type == "crawl":
            print(f"[Task Crawl] URL: {event.data.result.url}")

    elif event_type == "task-output":
        print(f"[Task Complete] Task ID: {event.task_id}")

    elif event_type == "research-output":
        if event.output.output_type == "completed":
            print("\n[Research Complete]")
            print(f"  Output length: {len(event.output.content)} characters")
            print(f"  Total cost: ${event.output.cost_dollars.total:.4f}")
            print(f"  Searches performed: {event.output.cost_dollars.num_searches}")
            print(f"  Pages crawled: {event.output.cost_dollars.num_pages}")
            print(f"  Reasoning tokens: {event.output.cost_dollars.reasoning_tokens}")
            print("\nFinal output preview:")
            print(event.output.content[:500] + "...")
        elif event.output.output_type == "failed":
            print(f"\n[Research Failed] Error: {event.output.error}")

print("\nStreaming complete!")
