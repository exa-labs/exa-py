"""Integration tests for search() method with contents options."""

import pytest


class TestSearchContentsOptions:
    """Test suite for search() contents behavior."""

    TEST_QUERY = "invasive ant species California"

    def test_defaults_to_text_contents_with_10k_max_characters(self, exa):
        """Verify search() returns text contents with 10,000 max chars by default."""
        response = exa.search(self.TEST_QUERY, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 10_000

    def test_returns_no_contents_when_explicitly_false(self, exa):
        """Verify search() returns no contents when contents=False."""
        response = exa.search(self.TEST_QUERY, contents=False, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is None
        assert sample_result.summary is None

    def test_returns_text_contents_when_explicitly_requested(self, exa):
        """Verify search() returns text when explicitly requested."""
        response = exa.search(self.TEST_QUERY, contents={"text": True}, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100

    def test_returns_text_with_custom_max_characters(self, exa):
        """Verify search() respects custom maxCharacters."""
        max_chars = 500
        response = exa.search(
            self.TEST_QUERY,
            contents={"text": {"max_characters": max_chars}},
            num_results=2,
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) <= max_chars

    @pytest.mark.timeout(15)
    def test_returns_summary_when_requested(self, exa):
        """Verify search() returns summary when requested."""
        response = exa.search(
            self.TEST_QUERY, contents={"summary": True}, num_results=2
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.summary is not None
        assert len(sample_result.summary) > 10
        assert sample_result.text is None

    @pytest.mark.timeout(20)
    def test_returns_both_text_and_summary(self, exa):
        """Verify search() can return both text and summary."""
        response = exa.search(
            self.TEST_QUERY,
            contents={"text": {"max_characters": 1000}, "summary": True},
            num_results=2,
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100
        assert len(sample_result.text) <= 1000
        assert sample_result.summary is not None
        assert len(sample_result.summary) > 10

    def test_defaults_to_text_when_passing_other_options(self, exa):
        """Verify search() defaults to text even with other options."""
        response = exa.search(self.TEST_QUERY, num_results=3, type="fast")

        assert len(response.results) == 3
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100


@pytest.mark.asyncio
class TestAsyncSearchContentsOptions:
    """Test suite for async search() contents behavior."""

    TEST_QUERY = "invasive ant species California"

    async def test_async_defaults_to_text_contents(self, async_exa):
        """Verify async search() returns text contents by default."""
        response = await async_exa.search(self.TEST_QUERY, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 10_000

    async def test_async_returns_no_contents_when_false(self, async_exa):
        """Verify async search() returns no contents when contents=False."""
        response = await async_exa.search(
            self.TEST_QUERY, contents=False, num_results=2
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is None
        assert sample_result.summary is None
