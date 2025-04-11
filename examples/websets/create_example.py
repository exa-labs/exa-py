from exa_py import Exa
import os

from exa_py.websets.types import CreateWebsetParameters, CreateEnrichmentParameters

# Use a mock API key for testing
exa = Exa("mock_api_key")

# Create Webset
response = exa.websets.create(
    params=CreateWebsetParameters(
        search={
            "query": "Tech companies in San Francisco with more than 20 and less than 100 employees",
            "count": 10,
        },
        enrichments=[
            CreateEnrichmentParameters(
                description="LinkedIn profile of VP of Engineering or related role",
                format="text",
            ),
        ],
    )
)

# Wait until Webset completes
webset = exa.websets.wait_until_idle(response.id)

# Retrieve Webset Items
response = exa.websets.items.list(webset_id=response.id)

for item in response.data:
    print(item)
