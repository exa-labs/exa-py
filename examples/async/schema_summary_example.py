import os
import json
from exa_py import AsyncExa
from exa_py.api import JSONSchema  # Import the JSONSchema type for clarity

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = AsyncExa(EXA_API_KEY)

# Define a JSON schema for structured summary output.
company_schema: JSONSchema = {
    # Originally $schema, but schema_ is used for python compatibility. Converted to $schema by the API.
    "schema_": "http://json-schema.org/draft-07/schema#",
    "title": "Company Information",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "The name of the company"
        },
        "industry": {
            "type": "string", 
            "description": "The industry the company operates in"
        },
        "foundedYear": {
            "type": "number",
            "description": "The year the company was founded"
        },
        "keyProducts": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of key products or services offered by the company"
        },
        "competitors": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of main competitors"
        }
    },
    "required": ["name", "industry"]
}

async def main():
    # Search and get structured summary using the schema.
    print("Searching for company information with structured schema...")
    search_response = await exa.search_and_contents(
        "OpenAI company information",
        summary={
            "schema": company_schema
        },
        category="company",
        num_results=3
    )

    # Display the results.
    print("\nStructured summaries:")
    for index, result in enumerate(search_response.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")
        
        if result.summary:
            # Try to parse the summary as JSON.
            try:
                structured_data = json.loads(result.summary)
                print(f"Structured data: {json.dumps(structured_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Summary (not structured): {result.summary}")
        else:
            print("No summary available")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
