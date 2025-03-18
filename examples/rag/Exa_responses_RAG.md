# RAG with OpenAI's Responses API and Exa

LLMs are powerful because they compress large amounts of data and patterns into a format that allows convenient access, but this compression isn't lossless. Exa can bring the most relevant data into context. This lets us combine the compressed data of the LLM with a select quantity of uncompressed data for the problem at hand for the best generations possible.

Exa's SDKs make incorporating quality data into your LLM pipelines quick and painless. The latest version of Exa's wrapper makes it even easier by working with OpenAI's new Responses API. Install the SDK by running this command in your terminal:

`pip install exa-py openai`

```python
# Now, import the Exa class and pass your API key to it.
from exa_py import Exa
import os

my_exa_api_key = os.environ.get("EXA_API_KEY")
if not my_exa_api_key:
    raise ValueError("EXA_API_KEY environment variable not set")
exa = Exa(my_exa_api_key)
```

For our example, we'll set up Exa to answer questions with OpenAI's GPT-4o model using the new Responses API. The key advantage is that the model can now decide when it needs to search for information and what to search for.

```python
# Set up OpenAI's SDK
from openai import OpenAI

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai_client = OpenAI(api_key=openai_api_key)

# Wrap the OpenAI client with Exa functionality
# This enhances both chat.completions.create and responses.create methods
exa.wrap(openai_client)
```

Now, we just need some questions to answer!

```python
questions = [
    "How did bats evolve their wings?",
    "How did Rome defend Italy from Hannibal?",
    "What are the latest developments in quantum computing?"  # Current information question
]
```

While LLMs can answer some questions on their own, they have limitations:
- LLMs don't have knowledge past when their training was stopped, so they can't know about recent events
- If an LLM doesn't know the answer, it will often 'hallucinate' a correct-sounding response, and it can be difficult and inconvenient to distinguish these from correct answers
- Because of the opaque manner of generation and the problems mentioned above, it is difficult to trust an LLM's responses when accuracy is [important](https://www.forbes.com/sites/mollybohannon/2023/06/08/lawyer-used-chatgpt-in-court-and-cited-fake-cases-a-judge-is-considering-sanctions/?sh=27194eb67c7f)

Let's use Exa with the OpenAI Responses API to overcome these limitations:

```python
# Define a helper function to process each question with our wrapped client
def answer_with_exa_rag(question):
    """Use OpenAI Responses API with Exa wrapper to answer a question with current web data."""
    print(f"\nQuestion: {question}")
    
    # Define the system message
    system_message = {
        "role": "system", 
        "content": "You are a helpful assistant. Use web search when you need current or specific information. Always cite your sources."
    }
    
    # Create messages with the user's question
    messages = [
        system_message,
        {"role": "user", "content": question}
    ]

    # Send request to OpenAI - the Exa wrapper will handle the search if needed
    print("Sending request to OpenAI with Exa wrapper...")
    response = openai_client.responses.create(
        model="gpt-4o",
        input=messages
    )
    
    # Check if a search was performed (the wrapper adds exa_result to the response if search was done)
    if hasattr(response, 'exa_result'):
        print("\nExa search was performed!")
        citations = [{"url": result.url, "title": result.title} for result in response.exa_result.results]
        return response.output_text, citations
    else:
        print("\nOpenAI provided an answer without needing to search the web.")
        return response.output_text, None

# Process each question
for question in questions:
    answer, citations = answer_with_exa_rag(question)
    print(f"\nAnswer: {answer}")
    
    if citations:
        print("\nSources:")
        for i, citation in enumerate(citations, 1):
            print(f"[{i}] {citation['title']}: {citation['url']}")
    print("\n" + "-"*80)
```

The beauty of this approach is that the model decides when it needs to search for information. For questions about recent events or specialized topics, it will likely trigger a search. For general knowledge questions that the model is confident about, it may not need to search.

Let's try a more complex example - using Exa to find academic sources about a specific concept:

```python
# Example with a complex paragraph about an economic theory
paragraph = """Georgism, also known as Geoism, is an economic philosophy and ideology named after the American political economist Henry George (1839–1897). This doctrine advocates for the societal collective, rather than individual property owners, to capture the economic value derived from land and other natural resources. To this end, Georgism proposes a single tax on the unimproved value of land, known as a "land value tax," asserting that this would deter speculative land holding and promote efficient use of valuable resources."""

question = f"What are the most important academic papers about Georgism? Please provide links to papers and a brief explanation of each."

answer, citations = answer_with_exa_rag(question)
print(f"\nAnswer: {answer}")

if citations:
    print("\nSources:")
    for i, citation in enumerate(citations, 1):
        print(f"[{i}] {citation['title']}: {citation['url']}")
```

## How the Exa Wrapper Works with OpenAI Responses API

Behind the scenes, the Exa wrapper:

1. Adds an Exa web search tool to the OpenAI model
2. When the model decides it needs to search for information, it calls the Exa tool with a search query
3. The wrapper intercepts this call, performs the actual search using Exa's API
4. The search results are passed back to the model
5. The model then uses this information to generate a more informed, accurate response

The main benefit compared to the previous approach is that the AI itself decides when and what to search for, rather than us having to manually create search queries for every question.

Using Exa with the OpenAI Responses API, you get:
- Up-to-date information for current events
- Verified facts with citations to reduce hallucinations 
- Dynamic searches that occur only when the model needs them
- A cleaner implementation with less code

For more information on how you can leverage Exa's capabilities, check out [this article](https://docs.exa.ai/reference/openai-responses-api-with-exa).