#!/usr/bin/env python
# coding: utf-8

# # RAG with OpenAI's Responses API and Exa

# LLMs are powerful but their compression of knowledge isn't perfect. Exa can bring the most relevant data 
# into context, allowing us to combine the LLM's capabilities with current, accurate information from the web.

# This example shows how to use Exa's wrapper with OpenAI's Responses API for seamless RAG integration.

# Install the SDKs by running these commands in your terminal:
# `pip install exa-py openai`

# Import the necessary libraries
import os
from exa_py import Exa
from openai import OpenAI

# Set up API clients with API keys
my_exa_api_key = os.environ.get("EXA_API_KEY")
if not my_exa_api_key:
    raise ValueError("EXA_API_KEY environment variable not set")
exa = Exa(my_exa_api_key)

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai_client = OpenAI(api_key=openai_api_key)

# Wrap the OpenAI client with Exa functionality
# This will enhance both chat.completions.create and responses.create methods
exa.wrap(openai_client)

# Define the system message that instructs the LLM to use web search when needed
system_message = {
    "role": "system", 
    "content": "You are a helpful assistant. Use web search when you need current or specific information. Always cite your sources."
}

# Now, let's define some questions to answer
questions = [
    "How did bats evolve their wings?",
    "How did Rome defend Italy from Hannibal?",
    "What are the latest developments in quantum computing?"
]

# Let's create a function to handle the RAG process with the Responses API using our wrapper
def answer_with_exa_rag(question):
    """Use OpenAI Responses API with Exa wrapper to answer a question with current web data."""
    print(f"\nQuestion: {question}")
    
    # Create messages with the user's question
    messages = [
        system_message,
        {"role": "user", "content": question}
    ]

    # Send request to OpenAI - the Exa wrapper will handle the search if needed
    print("Sending request to OpenAI with Exa wrapper...")
    response = openai_client.responses.create(
        model="gpt-4o",
        input=messages,
        # The Exa wrapper handles tool definition and function calls automatically
    )
    
    # The wrapper will have added exa_result to the response if a search was performed
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

# Let's try a more complex example - searching based on a paragraph
print("\n\nAdvanced Example: Finding academic sources related to a concept")

paragraph = """Georgism, also known as Georgism, is an economic philosophy and ideology named after the American political economist Henry George (1839–1897). This doctrine advocates for the societal collective, rather than individual property owners, to capture the economic value derived from land and other natural resources. To this end, Georgism proposes a single tax on the unimproved value of land, known as a "land value tax," asserting that this would deter speculative land holding and promote efficient use of valuable resources."""

question = "What are the most important academic papers about Georgism? Please provide links to papers and a brief explanation of each."

answer, citations = answer_with_exa_rag(question)
print(f"\nAnswer: {answer}")

if citations:
    print("\nSources:")
    for i, citation in enumerate(citations, 1):
        print(f"[{i}] {citation['title']}: {citation['url']}")