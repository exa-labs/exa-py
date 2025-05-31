import os
import asyncio
from openai import AsyncOpenAI


async def main():
    client = AsyncOpenAI(
        base_url="https://api.exa.ai",
        api_key=os.environ["EXA_API_KEY"],
    )

    completion = await client.chat.completions.create(
        model="exa",
        messages=[
            {
                "role": "user",
                "content": "What makes some LLMs so much better than others?",
            }
        ],
        stream=True,
    )

    async for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
