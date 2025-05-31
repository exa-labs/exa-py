import os
import json
import asyncio
from exa_py import AsyncExa

EXA_API_KEY = os.environ.get("EXA_API_KEY")

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = AsyncExa(EXA_API_KEY)

examples = [
    {
        "instructions": (
            "Summarize the history of San Francisco highlighting one or two major "
            "events for each decade from 1850 to 1950"
        ),
        "schema": {
            "type": "object",
            "required": ["timeline"],
            "properties": {
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["decade", "notableEvents"],
                        "properties": {
                            "decade": {
                                "type": "string",
                                "description": 'Decade label e.g. "1850s"',
                            },
                            "notableEvents": {
                                "type": "string",
                                "description": "A summary of notable events.",
                            },
                        },
                    },
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "instructions": (
            "Compile three major news stories related to environmental policy from "
            "the last week. For each story, include the article title, publication "
            "name, publication date, and a one-sentence summary."
        ),
        "schema": {
            "type": "object",
            "required": ["stories"],
            "properties": {
                "stories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "publication", "date", "summary"],
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Headline of the article.",
                            },
                            "publication": {
                                "type": "string",
                                "description": "Name of the news outlet.",
                            },
                            "date": {
                                "type": "string",
                                "description": "Publication date in ISO-8601 format.",
                            },
                            "summary": {
                                "type": "string",
                                "description": "One-sentence summary of the article.",
                            },
                        },
                    },
                }
            },
            "additionalProperties": False,
        },
    },
]


async def main():
    created = await asyncio.gather(
        *[
            exa.research.create_task(
                instructions=ex["instructions"],
                model="exa-research",
                output_schema=ex["schema"],
            )
            for ex in examples
        ]
    )

    task_ids = [t.id for t in created]
    print("Created Task IDs:", task_ids)

    list_response = await exa.research.list()
    retrieved_ids = [t.id for t in list_response.data]
    print(
        "All created tasks present in list:",
        all(tid in retrieved_ids for tid in task_ids),
    )
    print("Polling until research completion…")

    results = await asyncio.gather(*[exa.research.poll_task(tid) for tid in task_ids])

    for res in results:
        print(f"Final Task State for {res.id}:")
        print(json.dumps(res.data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
