from exa_py import Exa
import os

from exa_py.websets.core.model import CreateWebsetParameters, CreateEnrichmentParameters

exa = Exa("0db316b5-679a-460f-9c76-b66a772078bb", base_url="https://api.exa.sh")

# Create Webset
response = exa.websets.create(
    params=CreateWebsetParameters(
        external_id="test-webset",
        search={
            "query": "Engineers based in San Francisco",
            "count": 10,
        },
        # enrichments=[
        #     CreateEnrichmentParameters(
        #         description="LinkedIn profile of VP of Engineering or related role",
        #         format="text",
        #     ),
        # ],
    )
)

# Wait until Webset completes
webset = exa.websets.waitUntilIdle(response.id)


# Retrieve Webset Items
response = exa.websets.items.list(id=response.id)

for item in response.data:
    print(item)
