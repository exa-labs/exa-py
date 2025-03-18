#!/usr/bin/env python
# coding: utf-8

# # RAG: Answer your questions with Exa and OpenAI's Responses API

# This example demonstrates how to use Exa with OpenAI's new responses API
# for retrieval-augmented generation.

# Install the required packages:
# pip install exa-py openai

from exa_py import Exa
from openai import OpenAI
import os

# Set up Exa client
my_exa_api_key = os.environ.get("EXA_API_KEY")
if not my_exa_api_key:
    raise ValueError("EXA_API_KEY environment variable not set")
exa = Exa(my_exa_api_key)

# Set up OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai_client = OpenAI(api_key=openai_api_key)

# Wrap the OpenAI client with Exa functionality
openai_client = exa.wrap(openai_client)

# Define some questions to answer
questions = [
    "How did bats evolve their wings?",
    "How did Rome defend Italy from Hannibal?",
]

# Function to get answers using the responses API with Exa integration
def get_answer_with_exa(question):
    """Get an answer using Exa search through OpenAI's Responses API."""
    response = openai_client.responses.create(
        model="gpt-4",
        input=[
            {
                "role": "system",
                "content": "You are a helpful assistant. When users ask questions, use the exa_search function to find relevant information and provide detailed answers with citations."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        tools=[{
            "type": "web_search_exa",
            "config": {
                "num_results": 3,
                "text": {
                    "max_characters": 2000
                }
            }
        }]
    )
    
    # Extract answer text from the response
    answer = ""
    if hasattr(response, 'output'):
        for item in response.output:
            if hasattr(item, 'content'):
                answer += item.content[0].text
    
    # Format the response with question and answer
    formatted_response = {
        "question": question,
        "answer": answer,
    }
    return formatted_response

    
# Get answers for all questions
responses = []
for question in questions:
    response = get_answer_with_exa(question)
    responses.append(response)

# Display the results
print("\n=== RESPONSES WITH EXA SEARCH ===\n")
for response in responses:
    if response:
        print(f"Question: {response['question']}")
        print(f"Answer: {response['answer']}")
        print("\n---\n")
    else:
        print(f"No response found for question: {question}")

# Example for a more complex query with paragraph input
paragraph = """Georgism, also known as Georgism, is an economic philosophy and ideology named after the American political economist Henry George (1839–1897). This doctrine advocates for the societal collective, rather than individual property owners, to capture the economic value derived from land and other natural resources. To this end, Georgism proposes a single tax on the unimproved value of land, known as a "land value tax," asserting that this would deter speculative land holding and promote efficient use of valuable resources. Adherents argue that because the supply of land is fundamentally inelastic, taxing it will not deter its availability or use, unlike other forms of taxation. Georgism differs from Marxism and capitalism, underscoring the distinction between common and private property while largely contending that individuals should own the fruits of their labor."""

# Get academic sources using responses API
response = openai_client.responses.create(
    model="gpt-4o",
    input=[
        {"role": "user", "content": f"Find the best academic sources about the following economic theory: {paragraph}"}
    ],
    tools=[
        {
            "type": "web_search_exa",
            "config": {
                "num_results": 5
            }
        }
    ]
)

print("\n=== ACADEMIC SOURCES FOR GEORGISM ===\n")
answer = ""
for item in response.output:
    if item.type == "text":
        answer += item.text

print(answer)

if hasattr(response, "exa_result"):
    print("\n=== RAW EXA SEARCH RESULTS ===\n")
    for result in response.exa_result.results:
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        if hasattr(result, 'highlights') and result.highlights:
            print("Highlight:", result.highlights[0])
        print()
