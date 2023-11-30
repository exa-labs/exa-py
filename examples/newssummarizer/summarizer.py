from metaphor_python import Metaphor
import openai

from datetime import datetime, timedelta

METAPHOR_API_KEY = '' # insert or load your api key
OPENAI_API_KEY = '' # insert or load your api key

metaphor = Metaphor(METAPHOR_API_KEY)
openai.api_key = OPENAI_API_KEY

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

search_response = metaphor.search(
    search_query, use_autoprompt=True, start_published_date=date_cutoff
)

urls = [result.url for result in search_response.results]
print("URLs:")
for url in urls:
    print(url)

contents_result = search_response.get_contents()

content_item = contents_result.contents[0] # if you want more than one news article, you can loop through all the content items.
print(f"{len(contents_result.contents)} items total, printing the first one:")
print(content_item)

SYSTEM_MESSAGE = "You are a helpful assistant that briefly summarizes the content of a webpage. Summarize the users input."

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": content_item.extract},
    ],
)

summary = completion.choices[0].message.content

print(f"Summary for {content_item.url}:")
print(content_item.title)
print(summary)