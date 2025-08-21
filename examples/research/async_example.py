"""Example of using the async Research API client with all features."""

import asyncio
import os
from typing import List
from pydantic import BaseModel, Field
from exa_py import AsyncExa


class Framework(BaseModel):
    name: str = Field(description="Framework name")
    language: str = Field(description="Programming language")
    popularity: str = Field(description="Popularity level")
    use_case: str = Field(description="Primary use case")


class FrameworksReport(BaseModel):
    frameworks: List[Framework] = Field(description="List of web frameworks")
    summary: str = Field(description="Brief summary of findings")


async def main():
    # Initialize the async client
    api_key = os.environ.get("EXA_API_KEY")
    base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
    client = AsyncExa(api_key=api_key, api_base=base_url)

    print("Creating async research request with schema...")

    # 1. Create a research request with schema
    research = await client.research.create(
        instructions="""
        List 3 popular web development frameworks. For each framework provide:
        - Framework name
        - Programming language it uses
        - Its popularity level (high/medium/low)
        - Primary use case
        
        Also provide a brief summary of current web framework trends.

        Please keep you research brief, a few quick searches plus a summary should be plenty. Thanks!
        """,
        model="exa-research",
        output_schema=FrameworksReport,
    )

    print(f"Research created with ID: {research.research_id}")
    print(f"Initial status: {research.status}")

    # 2. Stream events as they happen
    print("\n=== Streaming events ===")
    event_count = 0
    async for event in await client.research.get(research.research_id, stream=True):
        event_count += 1
        event_type = event.event_type

        if event_type == "research-definition":
            print(f"[{event_count}] Research started")
        elif event_type == "plan-definition":
            print(f"[{event_count}] Plan created: {event.plan_id[:8]}...")
        elif event_type == "plan-operation" and event.data.type == "think":
            print(f"[{event_count}] Planning phase thinking...")
        elif event_type == "plan-output":
            if event.output.output_type == "tasks":
                print(
                    f"[{event_count}] Created {len(event.output.tasks_instructions)} tasks"
                )
        elif event_type == "task-definition":
            print(f"[{event_count}] Task started: {event.task_id[:8]}...")
        elif event_type == "task-operation":
            if event.data.type == "search":
                print(f"[{event_count}] Searching: {event.data.query[:50]}...")
            elif event.data.type == "crawl":
                print(f"[{event_count}] Crawling: {event.data.result.url[:50]}...")
        elif event_type == "task-output":
            print(f"[{event_count}] Task completed")
        elif event_type == "research-output":
            if event.output.output_type == "completed":
                print(f"[{event_count}] Research completed!")
                print(f"  Cost: ${event.output.cost_dollars.total:.4f}")
                print(f"  Searches: {event.output.cost_dollars.num_searches}")
            elif event.output.output_type == "failed":
                print(f"[{event_count}] Research failed: {event.output.error}")

    print(f"\nTotal events streamed: {event_count}")

    # 3. Get the research with typed output
    print("\n=== Getting research with typed output ===")
    typed_result = await client.research.get(
        research.research_id, output_schema=FrameworksReport
    )

    if typed_result.status == "completed":
        report = typed_result.parsed_output
        print(f"\nFrameworks found: {len(report.frameworks)}")
        for framework in report.frameworks:
            print(f"  - {framework.name} ({framework.language}): {framework.use_case}")
        print(f"\nSummary: {report.summary[:100]}...")

    # 4. Poll until finished (should return immediately since it's already done)
    print("\n=== Polling (should complete immediately) ===")
    final_result = await client.research.poll_until_finished(
        research.research_id, poll_interval=1000, timeout_ms=600000
    )
    print(f"Poll result status: {final_result.status}")

    # 5. List research requests
    print("\n=== Listing research requests ===")
    list_result = await client.research.list(limit=5)
    print(f"Found {len(list_result.data)} research requests")
    print(f"Has more: {list_result.has_more}")

    for r in list_result.data[:3]:  # Show first 3
        print(f"  - {r.research_id[:8]}... ({r.status}): {r.instructions[:50]}...")

    print("\n✅ Async example completed successfully!")

    # Close the client
    await client.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
