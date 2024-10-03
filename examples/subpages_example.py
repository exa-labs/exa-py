from exa_py import Exa
import os

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

# Fetch content from tesla.com, including 3 subpages
response = exa.get_contents(
    ids=["https://www.tesla.com"],
    subpages=3,
    subpage_target=["vehicles", "energy", "shop"],
    text=True,
    metadata=True
)

# Print the results
for result in response.results:
    print(f"URL: {result.url}")
    print(f"Title: {result.title}")
    print(f"Text snippet: {result.text[:200]}...")  # Print first 200 characters of text
    print("---")

    # Print subpage information if available
    if hasattr(result, 'subpages'):
        print("Subpages:")
        for subpage in result.subpages:
            print(f"  Subpage URL: {subpage.url}")
            print(f"  Subpage Title: {subpage.title}")
            print(f"  Subpage Text snippet: {subpage.text[:100]}...")  # Print first 100 characters of subpage text
            print("  ---")

    print("\n")
