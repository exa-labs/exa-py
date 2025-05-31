import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.exa.ai",
    api_key=os.environ["EXA_API_KEY"],
)

completion = client.chat.completions.create(
    model="exa",
    messages=[
        {"role": "user", "content": "What makes some LLMs so much better than others?"}
    ],
    stream=True,
)

for chunk in completion:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
