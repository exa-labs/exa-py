from exa_py import Exa
import os

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

response = exa.get_contents(
    ids=["firecrawl.dev"],
    subpages=4,
    # subpage_target= // specific subpage targets if you have any
    text=True,
    # livecrawl="always"
)

# Print the results
for result in response.results:
    print("=" * 80)
    print(f"Main URL: {result.url}")
    print(f"Title: {result.title}")
    print("-" * 40)
    print("Text snippet:")
    print(f"{result.text[:500]}...")  # Print first 500 characters of text
    print("\n")
