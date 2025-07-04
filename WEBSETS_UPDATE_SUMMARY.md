# Websets Client Update Summary

## Overview
Updated the websets client from the SDK to match the latest version of the OpenAPI specification from `https://raw.githubusercontent.com/exa-labs/openapi-spec/refs/heads/master/exa-websets-spec.yaml`.

## Changes Made

### 1. Enhanced Progress Model
**File:** `exa_py/websets/types.py`

Updated the `Progress` class to include new fields required by the latest spec:
- Added `analyzed` field: The number of results analyzed so far
- Added `time_left` field: The estimated time remaining in seconds (nullable)

### 2. New Recall Functionality
**File:** `exa_py/websets/types.py`

Added comprehensive recall metrics support with new classes:
- `RecallBounds`: Represents min/max bounds for recall estimates
- `RecallConfidence`: Enum for confidence levels (high, medium, low)
- `RecallExpected`: Contains total matches estimate with confidence and bounds
- `Recall`: Main recall metrics class with expected values and reasoning

### 3. Updated WebsetSearch Model
**File:** `exa_py/websets/types.py`

Enhanced the `WebsetSearch` class with:
- Added `exclude` field: List of sources to exclude from search results
- Added `recall` field: Optional recall metrics for the search

### 4. Updated Search Parameter Models
**File:** `exa_py/websets/types.py`

Updated search creation parameters:
- `CreateWebsetSearchParameters`: Added `recall` boolean field
- `CreateWebsetParametersSearch`: Added `recall` boolean field

## New Features Available

### Recall Metrics
- Users can now request recall estimates when creating searches
- Provides insights into total potential matches beyond found results
- Includes confidence levels and bounds for estimates

### Enhanced Progress Reporting
- More detailed progress information with analyzed count
- Time estimation for remaining search duration

### Search Exclusion
- Ability to exclude specific imports or websets from search results
- Prevents duplicate findings across different sources

## API Impact
These changes are backward compatible - existing code will continue to work as the new fields are optional or have default values.

## Files Modified
- `exa_py/websets/types.py`: Updated with new types and enhanced existing models

## Validation
- All Python syntax has been validated
- Changes maintain backward compatibility
- New fields follow the exact specification from the OpenAPI schema