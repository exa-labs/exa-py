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
        f"{company_name} official",
        num_results=5,
        include_urls=["*/about/*", "*/about-us/*", "*/company/*"],
        exclude_urls=["*/blog/*", "*/news/*", "*/press/*"]
    )
    
    for result in official_results.results[:3]:
        print(f"• {result.title}")
        print(f"  {result.url}\n")
    
    # 2. Find team/leadership pages
    print("2. Finding team and leadership information:")
    print("-" * 50)
    team_results = exa.search(
        f"{company_name} team leadership executives",
        num_results=5,
        include_urls=["*/team/*", "*/leadership/*", "*/people/*", "*/about/team/*"]
    )
    
    for result in team_results.results[:3]:
        print(f"• {result.title}")
        print(f"  {result.url}\n")
    
    # 3. Find contact information
    print("3. Finding contact information:")
    print("-" * 50)
    contact_results = exa.search_and_contents(
        f"{company_name} contact",
        num_results=3,
        include_urls=["*/contact/*", "*/contact-us/*", "*/get-in-touch/*"],
        text={"max_characters": 300}
    )
    
    for result in contact_results.results:
        print(f"• {result.title}")
        print(f"  {result.url}")
        if result.text:
            # Extract potential contact info preview
            preview = result.text[:150] + "..." if len(result.text) > 150 else result.text
            print(f"  Preview: {preview}\n")
    
    # 4. Find job postings/careers pages
    print("4. Finding career opportunities:")
    print("-" * 50)
    careers_results = exa.search(
        f"{company_name} careers hiring",
        num_results=5,
        include_urls=["*/careers/*", "*/jobs/*", "*/join/*", "*/hiring/*"]
    )
    
    for result in careers_results.results[:3]:
        print(f"• {result.title}")
        print(f"  {result.url}\n")
    
    # 5. Find investor relations (for public companies)
    print("5. Finding investor relations information:")
    print("-" * 50)
    investor_results = exa.search(
        f"{company_name} investor relations",
        num_results=3,
        include_urls=["*/investors/*", "*/investor-relations/*", "*/ir/*"]
    )
    
    if investor_results.results:
        for result in investor_results.results:
            print(f"• {result.title}")
            print(f"  {result.url}\n")
    else:
        print("No investor relations pages found (might be a private company)\n")
    
    # 6. Find product/service pages
    print("6. Finding product and service information:")
    print("-" * 50)
    product_results = exa.search(
        f"{company_name} products services",
        num_results=5,
        include_urls=["*/products/*", "*/services/*", "*/solutions/*", "*/platform/*"],
        exclude_urls=["*/blog/*", "*/support/*", "*/help/*"]
    )
    
    for result in product_results.results[:3]:
        print(f"• {result.title}")
        print(f"  {result.url}\n")


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