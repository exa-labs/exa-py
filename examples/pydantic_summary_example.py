"""
Pydantic Summary Example for Exa

This example demonstrates how to use Pydantic models with search and summary
to extract structured data from web content.
"""

import os
import json
from typing import List, Optional

from pydantic import BaseModel, Field
from exa_py import Exa

# Set up API key
EXA_API_KEY = os.environ.get("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")
EXA_BASE_URL = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")

exa = Exa(EXA_API_KEY, EXA_BASE_URL)

# ===============================================
# Pydantic Models for Structured Summaries
# ===============================================


class CompanyInformation(BaseModel):
    """Structured company data extraction. This should describe the company mentioned in the article, NOT the company publishing it."""

    name: str = Field(description="The name of the company")
    industry: str = Field(description="The industry the company operates in")
    founded_year: Optional[int] = Field(
        default=None, description="The year the company was founded"
    )
    headquarters: Optional[str] = Field(
        default=None, description="Location of company headquarters"
    )
    key_products: Optional[List[str]] = Field(
        default=None, description="List of key products or services"
    )
    market_cap: Optional[str] = Field(
        default=None, description="Market capitalization if available"
    )
    employee_count: Optional[str] = Field(
        default=None, description="Number of employees"
    )


class ResearchPaper(BaseModel):
    """Structured research paper information."""

    title: str = Field(description="Title of the research paper")
    authors: List[str] = Field(description="List of paper authors")
    publication_year: Optional[int] = Field(
        default=None, description="Year of publication"
    )
    journal: Optional[str] = Field(
        default=None, description="Journal or conference name"
    )
    abstract: str = Field(description="Abstract or summary of the paper")
    key_findings: Optional[List[str]] = Field(
        default=None, description="Main findings or contributions"
    )
    methodology: Optional[str] = Field(
        default=None, description="Research methodology used"
    )


class ProductInformation(BaseModel):
    """Structured product information extraction."""

    name: str = Field(description="Product name")
    manufacturer: str = Field(description="Company that makes the product")
    category: str = Field(description="Product category")
    price: Optional[str] = Field(default=None, description="Product price")
    key_features: Optional[List[str]] = Field(
        default=None, description="Main product features"
    )
    release_date: Optional[str] = Field(
        default=None, description="When the product was released"
    )
    target_audience: Optional[str] = Field(
        default=None, description="Who the product is designed for"
    )


class NewsEvent(BaseModel):
    """Simplified news event information."""

    headline: str = Field(description="Main headline of the news")
    summary: str = Field(description="Brief summary of what happened")
    key_points: Optional[List[str]] = Field(
        default=None, description="Main points from the article"
    )


# ===============================================
# Example Functions
# ===============================================


def extract_company_data():
    """Extract structured company information from search results."""
    print("Example 1: Company Information Extraction")
    print("=" * 40)

    response = exa.search_and_contents(
        "news articles about AI companies",
        summary={"schema": CompanyInformation},
        category="company",
        num_results=10,
    )

    for index, result in enumerate(response.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                company_data = json.loads(result.summary)

                print(f"Company: {company_data.get('name', 'N/A')}")
                print(f"Industry: {company_data.get('industry', 'N/A')}")

                if company_data.get("founded_year"):
                    print(f"Founded: {company_data['founded_year']}")

                if company_data.get("headquarters"):
                    print(f"Headquarters: {company_data['headquarters']}")

                if company_data.get("key_products"):
                    print("Key Products:")
                    for product in company_data["key_products"]:
                        print(f"  • {product}")

            except json.JSONDecodeError:
                print("Summary not in structured format")
        else:
            print("No summary available")


def extract_research_papers():
    """Extract structured information from research papers."""
    print("\n\nExample 2: Research Paper Analysis")
    print("=" * 40)

    response = exa.search_and_contents(
        "transformer architecture attention mechanism research paper",
        summary={"schema": ResearchPaper},
        category="research paper",
        num_results=10,
    )

    for index, result in enumerate(response.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                paper_data = json.loads(result.summary)

                print(f"Title: {paper_data.get('title', 'N/A')}")

                if paper_data.get("authors"):
                    authors = ", ".join(
                        paper_data["authors"][:3]
                    )  # Show first 3 authors
                    if len(paper_data["authors"]) > 3:
                        authors += f" (and {len(paper_data['authors']) - 3} others)"
                    print(f"Authors: {authors}")

                if paper_data.get("publication_year"):
                    print(f"Year: {paper_data['publication_year']}")

                if paper_data.get("journal"):
                    print(f"Published in: {paper_data['journal']}")

                if paper_data.get("key_findings"):
                    print("Key Findings:")
                    for finding in paper_data["key_findings"]:
                        print(f"  • {finding}")

            except json.JSONDecodeError:
                print("Summary not in structured format")
        else:
            print("No summary available")


def extract_product_info():
    """Extract structured product information."""
    print("\n\nExample 3: Product Information Extraction")
    print("=" * 40)

    response = exa.search_and_contents(
        "mechanical keyboards",
        summary={"schema": ProductInformation},
        num_results=10,
    )

    for index, result in enumerate(response.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                product_data = json.loads(result.summary)

                print(f"Product: {product_data.get('name', 'N/A')}")
                print(f"Manufacturer: {product_data.get('manufacturer', 'N/A')}")
                print(f"Category: {product_data.get('category', 'N/A')}")

                if product_data.get("price"):
                    print(f"Price: {product_data['price']}")

                if product_data.get("key_features"):
                    print("Key Features:")
                    for feature in product_data["key_features"]:
                        print(f"  • {feature}")

                if product_data.get("target_audience"):
                    print(f"Target Audience: {product_data['target_audience']}")

            except json.JSONDecodeError:
                print("Summary not in structured format")
        else:
            print("No summary available")


def extract_news_events():
    """Extract structured information from news articles."""
    print("\n\nExample 4: News Event Extraction")
    print("=" * 40)

    response = exa.search_and_contents(
        "recent AI breakthrough news 2024",
        summary={"schema": NewsEvent},
        category="news",
        num_results=10,
    )

    for index, result in enumerate(response.results):
        print(f"\nResult {index + 1}: {result.title}")
        print(f"URL: {result.url}")

        if result.summary:
            try:
                news_data = json.loads(result.summary)

                print(f"Headline: {news_data.get('headline', 'N/A')}")
                print(f"Summary: {news_data.get('summary', 'N/A')}")

                if news_data.get("key_points"):
                    print("Key Points:")
                    for point in news_data["key_points"]:
                        print(f"  • {point}")

            except json.JSONDecodeError:
                print("Summary not in structured format")
        else:
            print("No summary available")


# ===============================================
# Main Execution
# ===============================================


def main():
    print("Pydantic Summary Examples with Exa")
    print("Structured data extraction from web content")
    print("=" * 50)

    try:
        extract_company_data()
        extract_research_papers()
        extract_product_info()
        extract_news_events()

        print("\n" + "=" * 50)
        print("Examples completed successfully!")

    except Exception as e:
        print("Error:", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
