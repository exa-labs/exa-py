from metaphor_python import Metaphor
import openai

METAPHOR_API_KEY = '...' # insert or load your api key
OPENAI_API_KEY = '...' # insert or load your api key

openai.api_key = OPENAI_API_KEY
metaphor = Metaphor(METAPHOR_API_KEY)

def get_llm_response(system='You are a helpful assistant.', user = '', temperature = 1, model = 'gpt-3.5-turbo'):
    completion = openai.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ]
    )
    return completion.choices[0].message.content

# Let's generalize the prompt and call the search types (1) and (2) in case the LLM is sensitive to the names. We can replace them with different names programmatically to see what works best.
SEARCH_TYPE_EXPLANATION = """- (1) search is preferred because it lets us retrieve high quality, up-to-date, and semantically relevant data. It is especially suitable when a topic is well-known and popularly discussed on the Internet, allowing the machine learning model to retrieve contents which are more likely recommended by real humans.
- (2) search is only necessary when the topic is extremely specific, local or obscure. If the machine learning model might not know about the topic, but relevant documents can be found by directly matching the search query, (2) search is suitable.
"""

def decide_search_type(topic, choice_names = ['neural', 'keyword']):
    user_message = 'Decide whether to use (1) or (2) search for the provided research topic. Output your choice in a single word: either "(1)" or "(2)". Here is a guide that will help you choose:\n'
    user_message += SEARCH_TYPE_EXPLANATION
    user_message += f'Topic: {topic}\n'
    user_message += 'Search type: '
    user_message = user_message.replace('(1)', choice_names[0]).replace('(2)', choice_names[1])

    response = get_llm_response(
        system='You will be asked to make a choice between two options. Answer with your choice in a single word.',
        user=user_message,
        temperature=0
    )
    use_keyword = response.strip().lower().startswith(choice_names[1].lower())
    return 'keyword' if use_keyword else 'neural'

def create_keyword_query_generation_prompt(topic, n):
    return f"""I'm writing a research report on {topic} and need help coming up with Google keyword search queries.
Google keyword searches should just be a few words long. It should not be a complete sentence.
Please generate a diverse list of {n} Google keyword search queries that would be useful for writing a research report on ${topic}. Do not add any formatting or numbering to the queries."""

def create_neural_query_generation_prompt(topic, n):
    return f"""I'm writing a research report on {topic} and need help coming up with Metaphor keyword search queries.
Metaphor is a fully neural search engine that uses an embeddings based approach to search. Metaphor was trained on how people refer to content on the internet. The model is trained given the description to predict the link. For example, if someone tweets "This is an amazing, scientific article about Roman architecture: <link>", then our model is trained given the description to predict the link, and it is able to beautifully and super strongly learn associations between descriptions and the nature of the content (style, tone, entity type, etc) after being trained on many many examples. Because Metaphor was trained on examples of how people talk about links on the Internet, the actual Metaphor queries must actually be formed as if they are content recommendations that someone would make on the Internet where a highly relevant link would naturally follow the recommendation, such as the example shown above.
Metaphor neural search queries should be phrased like a person on the Internet indicating a webpage to a friend by describing its contents. It should end in a colon :.
Please generate a diverse list of {n} Metaphor neural search queries for informative and trustworthy sources useful for writing a research report on ${topic}. Do not add any quotations or numbering to the queries."""

def generate_search_queries(topic, n, searchType):
    if(searchType != 'keyword' and searchType != 'neural'):
        raise 'invalid searchType'
    user_prompt = create_neural_query_generation_prompt(topic, n) if searchType == 'neural' else create_keyword_query_generation_prompt(topic, n)
    completion = get_llm_response(
        system='The user will ask you to help generate some search queries. Respond with only the suggested queries in plain text with no extra formatting, each on it\'s own line.',
        user=user_prompt,
        temperature=1
    )
    queries = [s for s in completion.split('\n') if s.strip()][:n]
    return queries

def get_search_results(queries, type, linksPerQuery=2):
    results = []
    for query in queries:
        search_response = metaphor.search(query, type=type, num_results=linksPerQuery, use_autoprompt=False)
        results.extend(search_response.results)
    return results

def get_page_contents(search_results):
    contents_response = metaphor.get_contents(search_results)
    return contents_response.contents

def synthesize_report(topic, search_contents, content_slice = 750):
    inputData = ''.join([
        f'--START ITEM--\nURL: {item.url}\nCONTENT: {item.extract[:content_slice]}\n--END ITEM--\n'
        for item in search_contents
    ])
    return get_llm_response(
        system='You are a helpful research assistant. Write a report according to the user\'s instructions.',
        user='Input Data:\n' + inputData + f'Write a two paragraph research report about {topic} based on the provided information. Include as many sources as possible. Provide citations in the text using footnote notation ([#]). First provide the report, followed by a single "References" section that lists all the URLs used, in the format [#] <url>.',
        # model: 'gpt-4' # want a better report? use gpt-4
    )

def researcher(topic):
    search_type = decide_search_type(topic)
    search_queries = generate_search_queries(topic, 3, search_type)
    print(search_queries)
    search_results = get_search_results(search_queries, search_type)
    print(search_results[0])
    search_contents = get_page_contents([link.id for link in search_results])
    print(search_contents[0])
    report = synthesize_report(topic, search_contents)
    return report

print(researcher('renaissance art'))
print(researcher('xyzzy'))