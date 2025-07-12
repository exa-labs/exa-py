"""
Unit tests for URL filtering parameters (include_urls/exclude_urls).
These tests don't require an API key and test parameter validation.
"""

import pytest
from unittest.mock import MagicMock, patch
from exa_py import Exa
from exa_py.api import validate_search_options, SEARCH_OPTIONS_TYPES, FIND_SIMILAR_OPTIONS_TYPES


class TestUrlFilterValidation:
    """Test URL filter parameter validation."""
    
    def test_search_options_include_url_filters(self):
        """Test that SEARCH_OPTIONS_TYPES includes URL filter options."""
        assert "include_urls" in SEARCH_OPTIONS_TYPES
        assert "exclude_urls" in SEARCH_OPTIONS_TYPES
        assert SEARCH_OPTIONS_TYPES["include_urls"] == [list]
        assert SEARCH_OPTIONS_TYPES["exclude_urls"] == [list]
    
    def test_find_similar_options_include_url_filters(self):
        """Test that FIND_SIMILAR_OPTIONS_TYPES includes URL filter options."""
        assert "include_urls" in FIND_SIMILAR_OPTIONS_TYPES
        assert "exclude_urls" in FIND_SIMILAR_OPTIONS_TYPES
        assert FIND_SIMILAR_OPTIONS_TYPES["include_urls"] == [list]
        assert FIND_SIMILAR_OPTIONS_TYPES["exclude_urls"] == [list]
    
    def test_validate_search_options_accepts_url_filters(self):
        """Test that validate_search_options accepts URL filter parameters."""
        # Valid options should not raise
        options = {
            "query": "test",
            "include_urls": ["*/about/*", "*.edu/*"],
            "exclude_urls": ["*/blog/*", "*/news/*"]
        }
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
    
    def test_validate_search_options_rejects_invalid_url_filter_types(self):
        """Test that validate_search_options rejects invalid types for URL filters."""
        # String instead of list should raise
        options = {
            "query": "test",
            "include_urls": "*/about/*"  # Should be a list
        }
        with pytest.raises(ValueError, match="Invalid value for option 'include_urls'"):
            validate_search_options(options, SEARCH_OPTIONS_TYPES)
        
        # Dict instead of list should raise
        options = {
            "query": "test",
            "exclude_urls": {"pattern": "*/blog/*"}  # Should be a list
        }
        with pytest.raises(ValueError, match="Invalid value for option 'exclude_urls'"):
            validate_search_options(options, SEARCH_OPTIONS_TYPES)
    
    def test_validate_search_options_accepts_empty_lists(self):
        """Test that empty lists are valid for URL filters."""
        options = {
            "query": "test",
            "include_urls": [],
            "exclude_urls": []
        }
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
    
    def test_validate_search_options_accepts_none_values(self):
        """Test that None values are valid for optional URL filters."""
        options = {
            "query": "test",
            "include_urls": None,
            "exclude_urls": None
        }
        validate_search_options(options, SEARCH_OPTIONS_TYPES)


class TestUrlFilterIntegration:
    """Test URL filter integration with API methods (mocked)."""
    
    @patch('exa_py.api.requests.post')
    def test_search_passes_url_filters(self, mock_post):
        """Test that search method passes URL filters to API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "autopromptString": None
        }
        mock_post.return_value = mock_response
        
        exa = Exa("test-key")
        exa.search(
            "test query",
            include_urls=["*/contact/*"],
            exclude_urls=["*/blog/*"]
        )
        
        # Check that the request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # The data is passed as the second positional argument
        request_data = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('data', {})
        if isinstance(request_data, str):
            import json
            request_data = json.loads(request_data)
        
        assert "includeUrls" in request_data
        assert request_data["includeUrls"] == ["*/contact/*"]
        assert "excludeUrls" in request_data
        assert request_data["excludeUrls"] == ["*/blog/*"]
    
    @patch('exa_py.api.requests.post')
    def test_find_similar_passes_url_filters(self, mock_post):
        """Test that find_similar method passes URL filters to API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "autopromptString": None
        }
        mock_post.return_value = mock_response
        
        exa = Exa("test-key")
        exa.find_similar(
            "https://example.com",
            include_urls=["*.edu/*"],
            exclude_urls=["*/archive/*"]
        )
        
        # Check that the request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # The data is passed as the second positional argument
        request_data = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('data', {})
        if isinstance(request_data, str):
            import json
            request_data = json.loads(request_data)
        
        assert "includeUrls" in request_data
        assert request_data["includeUrls"] == ["*.edu/*"]
        assert "excludeUrls" in request_data
        assert request_data["excludeUrls"] == ["*/archive/*"]
    
    @patch('exa_py.api.requests.post')
    def test_search_and_contents_passes_url_filters(self, mock_post):
        """Test that search_and_contents method passes URL filters to API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "autopromptString": None
        }
        mock_post.return_value = mock_response
        
        exa = Exa("test-key")
        exa.search_and_contents(
            "test query",
            include_urls=["*/about/*", "*/team/*"],
            exclude_urls=["*/careers/*"],
            text=True
        )
        
        # Check that the request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # The data is passed as the second positional argument
        request_data = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('data', {})
        if isinstance(request_data, str):
            import json
            request_data = json.loads(request_data)
        
        assert "includeUrls" in request_data
        assert request_data["includeUrls"] == ["*/about/*", "*/team/*"]
        assert "excludeUrls" in request_data
        assert request_data["excludeUrls"] == ["*/careers/*"]
        assert "contents" in request_data  # Should have contents field
    
    @patch('exa_py.api.requests.post')
    def test_find_similar_and_contents_passes_url_filters(self, mock_post):
        """Test that find_similar_and_contents method passes URL filters to API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "autopromptString": None
        }
        mock_post.return_value = mock_response
        
        exa = Exa("test-key")
        exa.find_similar_and_contents(
            "https://example.com",
            include_urls=["www.linkedin.com/in/*"],
            text=True
        )
        
        # Check that the request was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # The data is passed as the second positional argument
        request_data = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('data', {})
        if isinstance(request_data, str):
            import json
            request_data = json.loads(request_data)
        
        assert "includeUrls" in request_data
        assert request_data["includeUrls"] == ["www.linkedin.com/in/*"]
        # exclude_urls not passed, so it shouldn't be in the request
        assert "excludeUrls" not in request_data or request_data["excludeUrls"] is None

    def test_url_filters_with_domain_filters_raises_error(self):
        """Test that using URL filters with domain filters raises an error."""
        with patch('exa_py.api.requests.post') as mock_post:
            # Mock the API to return an error when both are used together
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "Only one of includeDomains or excludeDomains can be provided with includeUrls/excludeUrls.",
                "requestId": "test-request-id"
            }
            mock_response.text = '{"error": "Only one of includeDomains or excludeDomains can be provided with includeUrls/excludeUrls."}'
            mock_post.return_value = mock_response
            
            exa = Exa("test-api-key")
            
            # Test include_urls with include_domains
            with pytest.raises(ValueError, match="includeDomains or excludeDomains"):
                exa.search(
                    "test query",
                    include_urls=["*/contact/*"],
                    include_domains=["example.com"]
                )
            
            # Test exclude_urls with exclude_domains  
            with pytest.raises(ValueError, match="includeDomains or excludeDomains"):
                exa.search(
                    "test query",
                    exclude_urls=["*/blog/*"],
                    exclude_domains=["spam.com"]
                )

    def test_url_filters_cannot_be_used_together(self):
        """Test that include_urls and exclude_urls cannot be used together."""
        with patch('exa_py.api.requests.post') as mock_post:
            # Mock the API to return an error when both are used together
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": "Cannot use both includeUrls and excludeUrls in the same request.",
                "requestId": "test-request-id"
            }
            mock_response.text = '{"error": "Cannot use both includeUrls and excludeUrls in the same request."}'
            mock_post.return_value = mock_response
            
            exa = Exa("test-api-key")
            
            # Test using both include_urls and exclude_urls together
            with pytest.raises(ValueError, match="includeUrls and excludeUrls"):
                exa.search(
                    "test query",
                    include_urls=["*/contact/*"],
                    exclude_urls=["*/blog/*"]
                )