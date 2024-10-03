from exa_py import Exa
import os

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

# Fetch content from tesla.com, including 20 subpages
response = exa.get_contents(
    ids=["firecrawl.dev"],
    subpages=10,
    # subpage_target= // specific subpage targets if you have any
    text=True,
    livecrawl="always"
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

    # Print subpage information if available
    if hasattr(result, 'subpages'):
        print("Subpages:")
        for i, subpage in enumerate(result.subpages, 1):
            print(f"  Subpage {i}:")
            print(f"  URL: {subpage.url}")
            print(f"  Title: {subpage.title}")
            print("  Text snippet:")
            print(f"  {subpage.text[:600]}...")  # Print first 200 characters of subpage text
            print("  " + "-" * 30)

    print("\n")
