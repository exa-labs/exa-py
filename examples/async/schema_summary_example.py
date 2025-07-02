import os
import json
from exa_py import AsyncExa
from exa_py.api import (
    JSONSchema,
)  # Import the JSONSchema type for clarity - DEPRECATED!

# New recommended approach using Pydantic
from pydantic import BaseModel, Field
from typing import List, Optional

EXA_API_KEY = os.environ.get("EXA_API_KEY")

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = AsyncExa(EXA_API_KEY)

# =====================================================
# NEW RECOMMENDED APPROACH: Using Pydantic Models
# =====================================================


class CompanyInformation(BaseModel):
    """Pydantic model for structured company data extraction."""

    name: str = Field(description="The name of the company")
    industry: str = Field(description="The industry the company operates in")
    founded_year: Optional[int] = Field(
        default=None, description="The year the company was founded"
    )
    key_products: Optional[List[str]] = Field(
        default=None, description="List of key products or services"
    )
    competitors: Optional[List[str]] = Field(
        default=None, description="List of main competitors"
    )


# =====================================================
# OLD APPROACH: Using JSONSchema TypedDict (DEPRECATED)
# =====================================================

# Define a JSON schema for structured summary output.
company_schema: JSONSchema = {
    # Originally $schema, but schema_ is used for python compatibility. Converted to $schema by the API.
    "schema_": "http://json-schema.org/draft-07/schema#",
    "title": "Company Information",
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "The name of the company"},
        "industry": {
            "type": "string",
            "description": "The industry the company operates in",
        },
        "foundedYear": {
            "type": "number",
            "description": "The year the company was founded",
        },
        "keyProducts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of key products or services offered by the company",
        },
        "competitors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of main competitors",
        },
    },
    "required": ["name", "industry"],
}


async def main():
    print("Async Schema Summary Example - Comparing Old vs New Approaches\n")
    print("=" * 60)

    # =====================================================
    # NEW RECOMMENDED APPROACH: Using Pydantic Models
    # =====================================================

    print("\n🆕 NEW APPROACH: Using Pydantic Models (Recommended)")
    print("Searching for company information with Pydantic schema...")

    search_response_new = await exa.search_and_contents(
        "OpenAI company information",
        summary={
            "schema": CompanyInformation  # Pass Pydantic model directly!
        },
        category="company",
        num_results=2,
    )

    print("\n✅ Structured summaries (Pydantic approach):")
    for index, result in enumerate(search_response_new.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                structured_data = json.loads(result.summary)
                print(f"Structured data: {json.dumps(structured_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Summary (not structured): {result.summary}")
        else:
            print("No summary available")

    # =====================================================
    # OLD APPROACH: Using JSONSchema TypedDict (DEPRECATED)
    # =====================================================

    print("\n\n🚨 LEGACY APPROACH: Using JSONSchema TypedDict (DEPRECATED)")
    print("⚠️  This approach is deprecated and will be removed in a future version.")
    print("⚠️  Please migrate to Pydantic models (shown above) for better type safety.")

    print("Searching with legacy JSONSchema approach...")
    search_response_legacy = await exa.search_and_contents(
        "Apple company information",
        summary={
            "schema": company_schema  # Still works for backward compatibility
        },
        category="company",
        num_results=1,
    )

    print("\n📋 Structured summaries (Legacy JSONSchema approach):")
    for index, result in enumerate(search_response_legacy.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                structured_data = json.loads(result.summary)
                print(f"Structured data: {json.dumps(structured_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Summary (not structured): {result.summary}")
        else:
            print("No summary available")

    print("\n" + "=" * 60)
    print("💡 Benefits of Pydantic approach:")
    print("  • Better IDE support with autocomplete")
    print("  • Automatic type validation")
    print("  • Cleaner, more readable code")
    print("  • Better integration with modern Python tools")
    print("  • No need to manually construct JSON Schema")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
