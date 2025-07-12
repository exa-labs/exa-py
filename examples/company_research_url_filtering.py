#!/usr/bin/env python3
"""
Example: Using URL filtering for efficient company research.

This example demonstrates how to use include_urls and exclude_urls to gather
specific types of information about companies, such as contact information,
team pages, and official announcements while filtering out noise.
"""

import os
from exa_py import Exa

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    raise ValueError("Please set EXA_API_KEY environment variable")

exa = Exa(api_key=api_key)


def research_company(company_name: str):
    """Research a company using targeted URL filtering."""
    print(f"\n=== Researching {company_name} ===\n")
    
    # 1. Find official company pages
    print("1. Finding official company information:")
    print("-" * 50)
    official_results = exa.search(
        f"{company_name} official website",
        num_results=5,
        include_urls=["*/about/*", "*/about-us/*", "*/company/*", "*/who-we-are/*"]
    )
    print(f"Found {len(official_results.results)} official pages")
    for result in official_results.results[:3]:
        print(f"  - {result.title}")
        print(f"    {result.url}\n")
    
    # 2. Find press releases and news
    print("\n2. Finding recent press releases:")
    print("-" * 50)
    press_results = exa.search_and_contents(
        f"{company_name} announcement",
        num_results=3,
        include_urls=["*/press/*", "*/news/*", "*/blog/*", "*/newsroom/*"],
        text={"max_characters": 300}
    )
    print(f"Found {len(press_results.results)} press releases")
    for result in press_results.results:
        print(f"  • {result.title}")
        print(f"    {result.url}")
        if result.text:
            preview = result.text[:150] + "..." if len(result.text) > 150 else result.text
            print(f"    Preview: {preview}\n")
    
    # 3. Find team information on LinkedIn
    print("\n3. Finding team members on LinkedIn:")
    team_results = exa.search(
        f"{company_name} employees team",
        num_results=5,
        include_urls=["www.linkedin.com/in/*", "linkedin.com/in/*"]
    )
    print(f"Found {len(team_results.results)} LinkedIn profiles")
    for result in team_results.results[:3]:
        print(f"  - {result.title}: {result.url}")


def find_competitors(company_name: str, industry: str):
    """Find competitor companies using URL filtering."""
    print(f"\n=== Finding competitors of {company_name} in {industry} ===\n")
    
    # Find similar company websites
    sample_url = f"https://www.{company_name.lower().replace(' ', '')}.com"
    
    similar_companies = exa.find_similar(
        sample_url,
        num_results=10,
        exclude_urls=["*/blog/*", "*/news/*", "*/wiki/*", "*/linkedin.com/*"]
    )
    
    print(f"Found {len(similar_companies.results)} similar company websites:")
    for i, result in enumerate(similar_companies.results[:5], 1):
        print(f"{i}. {result.title}")
        print(f"   {result.url}")
    print()


def main():
    """Run company research examples."""
    print("=== Company Research with URL Filtering ===")
    print("This example shows how to efficiently research companies")
    print("by filtering URLs to find specific types of information.\n")
    
    # Example companies to research
    companies = ["OpenAI", "Anthropic"]
    
    for company in companies:
        research_company(company)
    
    # Find competitors example
    find_competitors("OpenAI", "AI research")
    
    print("\n=== Summary ===")
    print("URL filtering helps you:")
    print("• Find official company information (not third-party coverage)")
    print("• Locate specific page types (contact, team, careers)")
    print("• Exclude irrelevant content (blogs, news, wikis)")
    print("• Focus your research on high-value pages")
    print("• Save time by getting targeted results")


if __name__ == "__main__":
    main()