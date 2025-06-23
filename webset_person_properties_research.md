# Webset Person Properties Research

## Current Implementation

The current `WebsetItemPersonPropertiesFields` class in `exa_py/websets/types.py` (lines 1442-1461) contains the following fields:

```python
class WebsetItemPersonPropertiesFields(ExaBaseModel):
    name: str
    """
    The name of the person
    """
    location: Optional[str] = None
    """
    The location of the person
    """
    position: Optional[str] = None
    """
    The current work position of the person
    """
    picture_url: Optional[AnyUrl] = Field(None, alias='pictureUrl')
    """
    The URL of the person's picture
    """
```

## Analysis of OpenAPI Spec

According to the user, new fields have been added to the Webset Item properties for people entities in the latest OpenAPI spec at:
https://raw.githubusercontent.com/exa-labs/openapi-spec/refs/heads/master/exa-websets-spec.yaml

## Next Steps

To complete this update, I need to:
1. Extract the WebsetItemPersonPropertiesFields schema from the OpenAPI spec
2. Compare it with the current implementation
3. Add any new fields that are missing
4. Update the Python types accordingly

## Common Fields That Might Be Added

Based on typical person entity properties, potential new fields could include:
- `email`: Optional[str] - person's email address
- `phone`: Optional[str] - person's phone number
- `company`: Optional[str] - current company
- `title`: Optional[str] - job title
- `bio`: Optional[str] - biography or description
- `social_profiles`: Optional[Dict] - social media profiles
- `skills`: Optional[List[str]] - list of skills
- `education`: Optional[str] - educational background
- `linkedin_url`: Optional[AnyUrl] - LinkedIn profile URL

## File Location

The types that need to be updated are in:
- `exa_py/websets/types.py` - line 1442 (`WebsetItemPersonPropertiesFields`)