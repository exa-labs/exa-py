## run pip install exa_py openai to install the two necessary packages
import openai
from exa_py import Exa
import textwrap
from datetime import datetime, timedelta

openai.api_key = "Paste your OpenAI API key here"
exa = Exa("Paste your Exa API key here")

SYSTEM_MESSAGE = "You are a helpful assistant that generates search queries based on user questions. Only generate one search query."
USER_QUESTION = "What's the recent news in physics this week?"

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_QUESTION},
    ],
)

search_query = completion.choices[0].message.content

print("Search query:")
print(search_query)

one_week_ago = (datetime.now() - timedelta(days=7))
date_cutoff = one_week_ago.strftime("%Y-%m-%d")

search_response = exa.search_and_contents(
    search_query, use_autoprompt=True, start_published_date=date_cutoff
)

urls = [result.url for result in search_response.results]
print("URLs:")
for url in urls:
    print(url)

results = search_response.results
result_item = results[0]
print(f"{len(results)} items total, printing the first one:")
print(result_item.text)

SYSTEM_MESSAGE = "You are a helpful assistant that briefly summarizes the content of a webpage. Summarize the users input."

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": result_item.text},
    ],
)

summary = completion.choices[0].message.content

print(f"Summary for {urls[0]}:")
print(result_item.title)
print(textwrap.fill(summary, 80))
