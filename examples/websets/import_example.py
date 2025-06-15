"""
Import Example

This example shows how to create an import and upload CSV data to Websets.
"""

import os
import requests
from exa_py import Exa
from exa_py.websets.types import (
    CreateImportParameters,
    ImportFormat,
    WebsetCompanyEntity,
    CsvImportConfig
)

# Initialize the Exa client
api_key = os.environ.get("EXA_API_KEY")
if not api_key:
    print("Please set EXA_API_KEY environment variable")
    print("Example: export EXA_API_KEY='your-api-key-here'")
    exit(1)

exa = Exa(api_key)

def main():
    # Sample CSV data for companies
    csv_data = """company_name,website_url,location
Apple Inc,https://www.apple.com,Cupertino California
Google LLC,https://www.google.com,Mountain View California
OpenAI,https://openai.com,San Francisco California
Microsoft Corporation,https://www.microsoft.com,Redmond Washington
Meta Platforms,https://www.meta.com,Menlo Park California"""

    print("Creating import...")
    
    # Create an import for company data
    import_response = exa.websets.imports.create(
        params=CreateImportParameters(
            title="Sample Company Data",
            format=ImportFormat.csv,
            entity=WebsetCompanyEntity(type="company"),
            size=len(csv_data.encode('utf-8')),
            count=5
        )
    )
    
    print(f"✓ Created import: {import_response.id}")
    print(f"  Upload URL valid until: {import_response.upload_valid_until}")
    
    # Upload the CSV data
    print("\nUploading CSV data...")
    upload_response = requests.put(
        import_response.upload_url,
        data=csv_data,
        headers={'Content-Type': 'text/csv'}
    )
    
    if upload_response.status_code == 200:
        print("✓ CSV data uploaded successfully")
    else:
        print(f"✗ Upload failed: {upload_response.status_code}")
        return
    
    # Wait for the import to complete
    print("\nWaiting for import to complete...")
    completed_import = exa.websets.imports.wait_until_completed(import_response.id)
    print(f"  Status: {completed_import.status}")
    print(f"  Records: {completed_import.count}")
    
    if completed_import.failed_reason:
        print(f"  Failed reason: {completed_import.failed_reason}")
        print(f"  Failed message: {completed_import.failed_message}")
    
    # Clean up
    print(f"\nDeleting import...")
    exa.websets.imports.delete(import_response.id)
    print(f"✓ Import deleted")

if __name__ == "__main__":
    main() 