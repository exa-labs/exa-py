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

  # autoprompted search
  results = exa.search("autopromptable query", use_autoprompt=True)

  # keyword search (non-neural)
  results = exa.search("Google-style query", type="keyword")

  # search with date filters
  results = exa.search("This is a Exa query:", start_published_date="2019-01-01", end_published_date="2019-01-31")

  # search with domain filters
  results = exa.search("This is a Exa query:", include_domains=["www.cnn.com", "www.nytimes.com"])

  # search and get text contents
  results = exa.search_and_contents("This is a Exa query:")

  # search and get highlights
  results = exa.search_and_contents("This is a Exa query:", highlights=True)

  # search and get contents with contents options
  results = exa.search_and_contents("This is a Exa query:", 
                                    text={"include_html_tags": True, "max_characters": 1000}, 
                                    highlights={"highlights_per_url": 2, "num_sentences": 1, "query": "This is the highlight query:"})
                                    
  # find similar documents
  results = exa.find_similar("https://example.com")

  # find similar excluding source domain
  results = exa.find_similar("https://example.com", exclude_source_domain=True)

  # find similar with contents
  results = exa.find_similar_and_contents("https://example.com", text=True, highlights=True)

  # get text contents
  results = exa.get_contents(["ids"])

  # get highlights
  results = exa.get_contents(["ids"], highlights=True)

  # get contents with contents options
  results = exa.get_contents(["ids"], 
                             text={"include_html_tags": True, "max_characters": 1000}, 
                             highlights={"highlights_per_url": 2, "num_sentences": 1, "query": "This is the highlight query:"})
```

