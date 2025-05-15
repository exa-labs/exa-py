# Exa

Exa (formerly Metaphor) API in Python

Note: This API is basically the same as `metaphor-python` but reflects new
features associated with Metaphor's rename to Exa. New site is https://exa.ai

## Installation

```bash
pip install exa_py
```

## Usage

Import the package and initialize the Exa client with your API key:

```python
from exa_py import Exa

exa = Exa(api_key="your-api-key")
```

## Common requests

```python

  # basic search
  results = exa.search("This is a Exa query:")

  # keyword search (non-neural)
  results = exa.search("Google-style query", type="keyword")

  # search with date filters
  results = exa.search("This is a Exa query:", start_published_date="2019-01-01", end_published_date="2019-01-31")

  # search with domain filters
  results = exa.search("This is a Exa query:", include_domains=["www.cnn.com", "www.nytimes.com"])

  # search and get text contents
  results = exa.search_and_contents("This is a Exa query:")

  # search and get contents with contents options
  results = exa.search_and_contents("This is a Exa query:",
                                    text={"include_html_tags": True, "max_characters": 1000})

  # find similar documents
  results = exa.find_similar("https://example.com")

  # find similar excluding source domain
  results = exa.find_similar("https://example.com", exclude_source_domain=True)

  # find similar with contents
  results = exa.find_similar_and_contents("https://example.com", text=True)

  # get text contents
  results = exa.get_contents(["tesla.com"])

  # get contents with contents options
  results = exa.get_contents(["urls"],
                             text={"include_html_tags": True, "max_characters": 1000})

  # basic answer
  response = exa.answer("This is a query to answer a question")

  # answer with full text, using the exa-pro model (sends 2 expanded quries to exa search)
  response = exa.answer("This is a query to answer a question", text=True, model="exa-pro")

  # answer with streaming
  response = exa.stream_answer("This is a query to answer:")

  # Print each chunk as it arrives when using the stream_answer method
  for chunk in response:
    print(chunk, end='', flush=True)

  # research task example – answer a question with citations
  # Example prompt & schema inspired by the TypeScript example.
  QUESTION = (
      "Summarize the history of San Francisco highlighting one or two major events "
      "for each decade from 1850 to 1950"
  )
  OUTPUT_SCHEMA: Dict[str, Any] = {
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
          },
      },
  }
  resp = exa.research.create_task(
      input_instructions=QUESTION,
      output_schema=OUTPUT_SCHEMA,
  )
```
