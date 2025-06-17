"""
Import Example

Clean CSV import with auto-calculated size/count.
"""

import os
from exa_py import Exa
from exa_py.websets.types import (
    CreateImportParameters,
    ImportFormat,
    WebsetCompanyEntity
)

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    print("Please set EXA_API_KEY environment variable")
    exit(1)

exa = Exa(api_key)

def main():
    # Sample CSV data
    csv_data = """company_name,website_url,location
Apple Inc,https://www.apple.com,Cupertino California
Google LLC,https://www.google.com,Mountain View California
OpenAI,https://openai.com,San Francisco California"""

    try:
        # Create import (size/count auto-calculated from CSV)
        params = CreateImportParameters(
            title="Sample Company Data",
            format=ImportFormat.csv,
            entity=WebsetCompanyEntity(type="company")
        )
        
        # Create and upload
        import_obj = exa.websets.imports.create(params, csv_data=csv_data)
        print(f"Import created: {import_obj.id}")
        
        # Wait for completion
        completed = exa.websets.imports.wait_until_completed(import_obj.id)
        print(f"Completed: {completed.count} records processed")
        
        # Clean up
        exa.websets.imports.delete(import_obj.id)
        print("Import deleted")
        
    except ValueError as e:
        if "Invalid API key" in str(e) or "x-api-key header is invalid" in str(e):
            print("Invalid API key. Get one from https://dashboard.exa.ai")
        else:
            raise e

if __name__ == "__main__":
    main() 