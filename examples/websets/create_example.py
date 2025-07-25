from exa_py import Exa
import os

from exa_py.websets.types import CreateWebsetParameters, CreateEnrichmentParameters

exa = Exa(os.environ.get("EXA_API_KEY"))

# Create Webset
response = exa.websets.create(
    params=CreateWebsetParameters(
        search={
            "query": "Tech companies in the United States with more than 20 and less than 100 employees",
            "count": 10,
        },
        enrichments=[
            CreateEnrichmentParameters(
                description="LinkedIn profile URL of VP of Engineering or related role",
                format="text",
            ),
        ],
    )
)

print("Webset created:", response.model_dump_json(indent=2))

# Wait until Webset completes
webset = exa.websets.wait_until_idle(response.id)

# Retrieve Webset Items
response = exa.websets.items.list(webset_id=response.id)

for item in response.data:
    print(item.model_dump_json(indent=2))
