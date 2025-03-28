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
        model="exa-pro",
    )
    print(response)

    #Answer with streaming
    response = await exa.stream_answer(
        "How close are we to meeting aliens?",
    )

    async for chunk in response:
        print(chunk, end='', flush=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
