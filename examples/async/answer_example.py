from exa_py import AsyncExa
import os

exa = AsyncExa(os.environ.get("EXA_API_KEY"))


async def main():
    # Basic answer
    response = await exa.answer("What is the population of the US?")
    print(response)

    # Answer with full text
    response = await exa.answer(
        "What is the meaning of life? ",
        text=True,
        model="exa",
    )
    print(response)

    # Answer with system prompt
    response = await exa.answer(
        "What is the latest valuation of SpaceX?",
        system_prompt="Answer only in a single sentence.",
    )
    print(response)

    # Answer with streaming
    response = await exa.stream_answer(
        "How close are we to meeting aliens?",
        system_prompt="Answer in a humorous tone.",
    )
    async for chunk in response:
        print(chunk, end="", flush=True)

    # Answer with system prompt
    response = await exa.answer(
        "What is the latest valuation of SpaceX?",
        output_schema={
            "type": "object",
            "required": ["answer"],
            "additionalProperties": False,
            "properties": {
                "answer": {"type": "number"},
            },
        },
    )
    print(response)

    response = await exa.answer("National museum", user_location="FR")
    print("Answer with user location", response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
