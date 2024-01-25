from exa_py import Exa
import openai
import os

from datetime import datetime, timedelta

EXA_API_KEY = os.environ.get("EXA_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

exa = Exa(EXA_API_KEY)
openai.api_key = OPENAI_API_KEY
openai.api_type = "openai"

SYSTEM_MESSAGE = "You are a helpful assistant that generates search queries based on user questions. Only generate one search query."
USER_QUESTION = "What's the recent news in physics this week?"

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_QUESTION},
    ],
)

search_query = completion.choices[0].message.content if completion.choices[0].message.content else ''

print("Search query:")
print(search_query)


one_week_ago = (datetime.now() - timedelta(days=7))
date_cutoff = one_week_ago.strftime("%Y-%m-%d")

search_response = exa.search_and_contents(
    search_query, use_autoprompt=True, start_published_date=date_cutoff, text=True
)

urls = [result.url for result in search_response.results]
print("URLs:")
for url in urls:
    print(url)

first_article_result = search_response.results[0]

SYSTEM_MESSAGE = "You are a helpful assistant that briefly summarizes the content of a webpage. Summarize the users input."

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": first_article_result.text[:1000]},
    ],
)

summary = completion.choices[0].message.content

print(f"Summary for {first_article_result.url}:")
print(first_article_result.title)
print(summary)
