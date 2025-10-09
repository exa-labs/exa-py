"""Example of using structured output schemas with Pydantic models."""

import os
from typing import List
from pydantic import BaseModel, Field
from exa_py import Exa

# Initialize the client
api_key = os.environ.get("EXA_API_KEY")
base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
client = Exa(api_key=api_key, base_url=base_url)


# Define a Pydantic model for structured output
class Company(BaseModel):
    name: str = Field(description="Company name")
    product: str = Field(description="Main product")


class CompaniesReport(BaseModel):
    companies: List[Company] = Field(description="List of companies")
    summary: str = Field(description="Brief summary")


# Create a research request with structured output
print("Creating research request with structured output schema...")
research = client.research.create(
    instructions="List 2 major tech companies with their main product. Provide a brief summary.",
    model="exa-research-fast",
    output_schema=CompaniesReport,
)

print(f"Research created with ID: {research.research_id}")

# Poll until complete, with typed output
print("\nWaiting for research to complete...")
completed = client.research.poll_until_finished(
    research.research_id,
    output_schema=CompaniesReport,
    poll_interval=3000,
    timeout_ms=600000,  # 10 minute timeout
)

print(f"\nResearch completed with status: {completed.status}")

if completed.status == "completed":
    # Access the typed output directly
    report = completed.parsed_output

    print("\n" + "=" * 60)
    print("AI COMPANIES RESEARCH REPORT")
    print("=" * 60)

    print(f"\nEXECUTIVE SUMMARY:\n{report.summary}")

    print(f"\nCOMPANIES ({len(report.companies)}):")
    for i, company in enumerate(report.companies, 1):
        print(f"  {i}. {company.name}: {company.product}")

    print(f"\nCost: ${completed.cost_dollars.total:.4f}")

elif completed.status == "failed":
    print(f"Research failed with error: {completed.error}")

# Alternative: Using dict schema instead of Pydantic
print("\n" + "=" * 60)
print("Example with dict schema:")
print("=" * 60)

dict_schema = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["answer", "confidence"],
}

research2 = client.research.create(
    instructions="What is the capital of Japan? Provide your answer and confidence level.",
    model="exa-research-fast",
    output_schema=dict_schema,
)

print(f"\nCreated research with dict schema: {research2.research_id}")

# Poll and get results
result = client.research.poll_until_finished(research2.research_id)
if result.status == "completed" and result.output.parsed:
    print("\nStructured output:")
    print(f"  Answer: {result.output.parsed['answer']}")
    print(f"  Confidence: {result.output.parsed['confidence']}")
