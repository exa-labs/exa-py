from exa_py import Exa
import os

from exa_py.websets.core.model import CreateWebsetParameters, CreateEnrichmentParameters

exa = Exa(os.environ.get("EXA_API_KEY"))

# Create Webset
response = exa.websets.create(
    params=CreateWebsetParameters(
        external_id="test-webset",
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
webset = exa.websets.waitUntilIdle(response.id)


# Retrieve Webset Items
response = exa.websets.items.list(id=response.id)

for item in response.data:
    print(item)
