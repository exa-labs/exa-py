#!/usr/bin/env python3
"""
Example demonstrating URL filtering with include_urls and exclude_urls parameters.

This example shows how to use the new URL filtering capabilities in Exa API
to refine search results based on URL patterns.

IMPORTANT: When using include_urls or exclude_urls, you cannot use 
include_domains or exclude_domains in the same request.
"""

import os
from exa_py import Exa

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    raise ValueError("Please set EXA_API_KEY environment variable")

exa = Exa(api_key=api_key)

print("=== Exa URL Filtering Examples ===\n")

# Example 1: Find contact pages for AI startups
print("1. Finding contact pages for AI startups:")
print("-" * 50)
results = exa.search(
    "AI startup artificial intelligence",
    num_results=5,
    include_urls=["*/contact/*", "*/contact-us/*", "*/about/contact/*"]
)
print(f"Found {len(results.results)} contact pages:")
for i, result in enumerate(results.results[:3], 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
print()

# Example 2: Exclude blog and news articles
print("2. Searching for technical content, excluding blogs and news:")
print("-" * 50)
results = exa.search(
    "machine learning algorithms",
    num_results=5,
    exclude_urls=["*/blog/*", "*/news/*", "*/press/*"]
)
print(f"Found {len(results.results)} non-blog/news results:")
for i, result in enumerate(results.results[:3], 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
print()

# Example 3: Find LinkedIn profiles
print("3. Finding LinkedIn profiles similar to a tech leader:")
print("-" * 50)
results = exa.find_similar(
    "https://www.linkedin.com/in/satyanadella/",
    num_results=5,
    include_urls=["www.linkedin.com/in/*", "linkedin.com/in/*"]
)
print(f"Found {len(results.results)} LinkedIn profiles:")
for i, result in enumerate(results.results[:3], 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
print()

# Example 4: Filter by domain extension
print("4. Finding only .edu educational resources:")
print("-" * 50)
results = exa.search(
    "quantum computing introduction",
    num_results=5,
    include_urls=["*.edu/*"]
)
print(f"Found {len(results.results)} educational resources:")
for i, result in enumerate(results.results[:3], 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
print()

# Example 5: Complex filtering with both include and exclude
print("5. Finding product pages, excluding reviews and comparisons:")
print("-" * 50)
try:
    results = exa.search(
        "best laptop 2024",
        num_results=5,
        include_urls=["*/products/*", "*/shop/*", "*/store/*"],
        exclude_urls=["*/review/*", "*/compare/*", "*/vs/*"]
    )
    print(f"Found {len(results.results)} product pages:")
    for i, result in enumerate(results.results[:3], 1):
        print(f"{i}. {result.title}")
        print(f"   URL: {result.url}")
except ValueError as e:
    print(f"Note: This example may fail if the API doesn't support both include and exclude URLs together.")
    print(f"Error: {str(e)}")
print()

# Example 6: Using with search_and_contents
print("6. Getting content from specific page types:")
print("-" * 50)
results = exa.search_and_contents(
    "company mission statement",
    num_results=3,
    include_urls=["*/about/*", "*/about-us/*", "*/mission/*"],
    text={"max_characters": 500}
)
print(f"Found {len(results.results)} about/mission pages with content:")
for i, result in enumerate(results.results, 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
    if result.text:
        preview = result.text[:200] + "..." if len(result.text) > 200 else result.text
        print(f"   Preview: {preview}")
    print()

# Example 7: Finding similar pages with URL constraints
print("7. Finding similar documentation pages:")
print("-" * 50)
results = exa.find_similar_and_contents(
    "https://docs.python.org/3/tutorial/",
    num_results=3,
    include_urls=["*/docs/*", "*/documentation/*", "*/guide/*"],
    exclude_urls=["*/api/*", "*/reference/*"],
    text=True
)
print(f"Found {len(results.results)} similar documentation pages:")
for i, result in enumerate(results.results, 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
    print()

print("\n=== Advanced Usage Tips ===")
print("1. Wildcards (*) can be used at the beginning or end of patterns")
print("2. Multiple patterns can be specified in a list")
print("3. include_urls and exclude_urls can be used together")
print("4. Patterns are case-sensitive")
print("5. IMPORTANT: Cannot use include_urls/exclude_urls with include_domains/exclude_domains")
print("6. Use these filters to:")
print("   - Find specific page types (contact, about, product pages)")
print("   - Filter by domain or subdomain patterns")
print("   - Exclude unwanted content types (ads, reviews, archives)")
print("   - Focus on specific platforms (LinkedIn, GitHub, etc.)")