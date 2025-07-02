"""
Comprehensive Pydantic Schema Example for Exa

This example demonstrates advanced usage of Pydantic models for structured data extraction
with the Exa API, including nested models, optional fields, and validation.
"""

import os
import json
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from exa_py import Exa

# Set up API key
EXA_API_KEY = os.environ.get("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = Exa(EXA_API_KEY)

# ===============================================
# Advanced Pydantic Models for Different Use Cases
# ===============================================


class IndustryType(str, Enum):
    """Enum for common industry types."""

    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class FundingRound(BaseModel):
    """Model for funding round information."""

    round_type: str = Field(description="Type of funding round (e.g., Series A, Seed)")
    amount: Optional[str] = Field(
        default=None, description="Amount raised in the round"
    )
    date: Optional[str] = Field(default=None, description="Date of the funding round")
    investors: Optional[List[str]] = Field(
        default=None, description="List of investors in the round"
    )


class CompanyFinancials(BaseModel):
    """Model for company financial information."""

    revenue: Optional[str] = Field(default=None, description="Annual revenue")
    valuation: Optional[str] = Field(default=None, description="Company valuation")
    employee_count: Optional[int] = Field(
        default=None, description="Number of employees"
    )
    funding_rounds: Optional[List[FundingRound]] = Field(
        default=None, description="Funding history"
    )


class Product(BaseModel):
    """Model for product information."""

    name: str = Field(description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    launch_date: Optional[str] = Field(default=None, description="Product launch date")
    target_market: Optional[str] = Field(
        default=None, description="Target market for the product"
    )


class CompanyProfile(BaseModel):
    """Comprehensive company profile model with nested structures."""

    name: str = Field(description="The official name of the company")
    industry: IndustryType = Field(description="Primary industry category")
    founded_year: Optional[int] = Field(
        default=None, description="Year the company was founded"
    )
    headquarters: Optional[str] = Field(
        default=None, description="Location of company headquarters"
    )

    # Business information
    business_model: Optional[str] = Field(
        default=None, description="Description of the business model"
    )
    key_products: Optional[List[Product]] = Field(
        default=None, description="List of key products/services"
    )
    target_customers: Optional[str] = Field(
        default=None, description="Description of target customer base"
    )

    # Financial and growth information
    financials: Optional[CompanyFinancials] = Field(
        default=None, description="Financial information"
    )

    # Market position
    competitors: Optional[List[str]] = Field(
        default=None, description="List of main competitors"
    )
    market_position: Optional[str] = Field(
        default=None, description="Position in the market"
    )

    # Leadership
    ceo: Optional[str] = Field(default=None, description="Name of the CEO")
    founders: Optional[List[str]] = Field(
        default=None, description="List of company founders"
    )


# ===============================================
# Simple Research Paper Model
# ===============================================


class Author(BaseModel):
    """Model for research paper author."""

    name: str = Field(description="Author's full name")
    affiliation: Optional[str] = Field(
        default=None, description="Author's institutional affiliation"
    )


class ResearchPaper(BaseModel):
    """Model for extracting research paper information."""

    title: str = Field(description="Title of the research paper")
    authors: List[Author] = Field(description="List of paper authors")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    publication_date: Optional[str] = Field(
        default=None, description="Publication date"
    )
    journal: Optional[str] = Field(
        default=None, description="Journal or conference name"
    )
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    keywords: Optional[List[str]] = Field(default=None, description="Keywords or tags")
    key_findings: Optional[List[str]] = Field(
        default=None, description="Main findings or contributions"
    )


# ===============================================
# News Article Model
# ===============================================


class NewsArticle(BaseModel):
    """Model for extracting news article information."""

    headline: str = Field(description="Main headline of the article")
    summary: str = Field(description="Brief summary of the article content")
    publication_date: Optional[str] = Field(
        default=None, description="Publication date"
    )
    author: Optional[str] = Field(default=None, description="Article author")
    key_points: Optional[List[str]] = Field(
        default=None, description="Main points discussed"
    )
    mentioned_companies: Optional[List[str]] = Field(
        default=None, description="Companies mentioned in the article"
    )
    stock_impact: Optional[str] = Field(
        default=None, description="Potential impact on stock prices"
    )


# ===============================================
# Example Usage Functions
# ===============================================


def analyze_company(company_name: str):
    """Analyze a company using the comprehensive CompanyProfile model."""
    print(f"\n{'=' * 60}")
    print(f"🔍 ANALYZING COMPANY: {company_name}")
    print(f"{'=' * 60}")

    search_response = exa.search_and_contents(
        f"{company_name} company profile business model financials",
        summary={"schema": CompanyProfile},
        category="company",
        num_results=3,
    )

    for i, result in enumerate(search_response.results, 1):
        print(f"\n📊 Result {i}: {result.title}")
        print(f"🔗 URL: {result.url}")

        if result.summary:
            try:
                # Parse the structured data
                company_data = json.loads(result.summary)

                # Display key information
                print(f"\n🏢 Company: {company_data.get('name', 'N/A')}")
                print(f"🏭 Industry: {company_data.get('industry', 'N/A')}")
                print(f"📅 Founded: {company_data.get('founded_year', 'N/A')}")
                print(f"🏠 HQ: {company_data.get('headquarters', 'N/A')}")

                if company_data.get("financials"):
                    fin = company_data["financials"]
                    print(f"💰 Revenue: {fin.get('revenue', 'N/A')}")
                    print(f"💎 Valuation: {fin.get('valuation', 'N/A')}")
                    print(f"👥 Employees: {fin.get('employee_count', 'N/A')}")

                if company_data.get("key_products"):
                    print(f"\n🛍️ Key Products:")
                    for product in company_data["key_products"][:3]:  # Show first 3
                        print(f"  • {product.get('name', 'Unknown')}")

                print(f"\n📋 Full structured data:")
                print(json.dumps(company_data, indent=2))

            except json.JSONDecodeError:
                print(f"⚠️ Could not parse structured data: {result.summary}")
        else:
            print("❌ No summary available")


def research_papers(topic: str):
    """Search for research papers on a specific topic."""
    print(f"\n{'=' * 60}")
    print(f"📚 RESEARCH PAPERS: {topic}")
    print(f"{'=' * 60}")

    search_response = exa.search_and_contents(
        f"{topic} research paper academic study",
        summary={"schema": ResearchPaper},
        num_results=2,
    )

    for i, result in enumerate(search_response.results, 1):
        print(f"\n📄 Paper {i}: {result.title}")
        print(f"🔗 URL: {result.url}")

        if result.summary:
            try:
                paper_data = json.loads(result.summary)
                print(f"\n📝 Title: {paper_data.get('title', 'N/A')}")

                if paper_data.get("authors"):
                    authors = [
                        author.get("name", "Unknown")
                        for author in paper_data["authors"]
                    ]
                    print(
                        f"✍️ Authors: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}"
                    )

                print(f"📅 Published: {paper_data.get('publication_date', 'N/A')}")
                print(f"📚 Journal: {paper_data.get('journal', 'N/A')}")

                if paper_data.get("key_findings"):
                    print(f"\n🔬 Key Findings:")
                    for finding in paper_data["key_findings"][:2]:
                        print(f"  • {finding}")

            except json.JSONDecodeError:
                print(f"⚠️ Could not parse structured data: {result.summary}")


def analyze_news(topic: str):
    """Analyze news articles about a specific topic."""
    print(f"\n{'=' * 60}")
    print(f"📰 NEWS ANALYSIS: {topic}")
    print(f"{'=' * 60}")

    search_response = exa.search_and_contents(
        f"{topic} news latest developments",
        summary={"schema": NewsArticle},
        category="news",
        num_results=2,
    )

    for i, result in enumerate(search_response.results, 1):
        print(f"\n📰 Article {i}: {result.title}")
        print(f"🔗 URL: {result.url}")

        if result.summary:
            try:
                news_data = json.loads(result.summary)
                print(f"\n📰 Headline: {news_data.get('headline', 'N/A')}")
                print(f"📅 Date: {news_data.get('publication_date', 'N/A')}")
                print(f"✍️ Author: {news_data.get('author', 'N/A')}")
                print(f"\n📝 Summary: {news_data.get('summary', 'N/A')}")

                if news_data.get("key_points"):
                    print(f"\n🎯 Key Points:")
                    for point in news_data["key_points"][:3]:
                        print(f"  • {point}")

                if news_data.get("mentioned_companies"):
                    companies = news_data["mentioned_companies"][:5]
                    print(f"\n🏢 Companies Mentioned: {', '.join(companies)}")

            except json.JSONDecodeError:
                print(f"⚠️ Could not parse structured data: {result.summary}")


# ===============================================
# Main Execution
# ===============================================


def main():
    print("🚀 Comprehensive Pydantic Schema Examples with Exa")
    print(
        "This example demonstrates advanced structured data extraction using Pydantic models."
    )

    try:
        # Example 1: Company Analysis
        analyze_company("Anthropic")

        # Example 2: Research Papers
        research_papers("machine learning transformers")

        # Example 3: News Analysis
        analyze_news("artificial intelligence")

        print(f"\n{'=' * 60}")
        print("✅ All examples completed successfully!")
        print("\n💡 Key Benefits of Pydantic Schemas:")
        print("  • Type safety and validation")
        print("  • Nested data structures")
        print("  • Custom validators")
        print("  • Automatic JSON Schema generation")
        print("  • Excellent IDE support")
        print("  • Self-documenting code")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
