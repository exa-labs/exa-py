"""Integration tests for find_similar() method with contents options."""

import pytest


class TestFindSimilarContentsOptions:
    """Test suite for find_similar() contents behavior."""

    TEST_URL = "https://en.wikipedia.org/wiki/Ant"

    def test_defaults_to_text_contents_with_20k_max_characters(self, exa):
        """Verify find_similar() returns text contents with 20,000 max chars by default."""
        response = exa.find_similar(self.TEST_URL, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 20_000

    def test_returns_no_contents_when_explicitly_false(self, exa):
        """Verify find_similar() returns no contents when contents=False."""
        response = exa.find_similar(self.TEST_URL, contents=False, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is None
        assert sample_result.summary is None

    def test_returns_text_contents_when_explicitly_requested(self, exa):
        """Verify find_similar() returns text when explicitly requested."""
        response = exa.find_similar(
            self.TEST_URL, contents={"text": True}, num_results=2
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100

    def test_returns_text_with_custom_max_characters(self, exa):
        """Verify find_similar() respects custom maxCharacters."""
        max_chars = 500
        response = exa.find_similar(
            self.TEST_URL,
            contents={"text": {"max_characters": max_chars}},
            num_results=2,
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) <= max_chars

    @pytest.mark.timeout(15)
    def test_returns_summary_when_requested(self, exa):
        """Verify find_similar() returns summary when requested."""
        response = exa.find_similar(
            self.TEST_URL, contents={"summary": True}, num_results=2
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.summary is not None
        assert len(sample_result.summary) > 10
        assert sample_result.text is None

    @pytest.mark.timeout(20)
    def test_returns_both_text_and_summary(self, exa):
        """Verify find_similar() can return both text and summary."""
        response = exa.find_similar(
            self.TEST_URL,
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
        """Verify find_similar() defaults to text even with other options."""
        response = exa.find_similar(
            self.TEST_URL, num_results=3, exclude_source_domain=True
        )

        assert len(response.results) == 3
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100


@pytest.mark.asyncio
class TestAsyncFindSimilarContentsOptions:
    """Test suite for async find_similar() contents behavior."""

    TEST_URL = "https://en.wikipedia.org/wiki/Ant"

    async def test_async_defaults_to_text_contents(self, async_exa):
        """Verify async find_similar() returns text contents by default."""
        response = await async_exa.find_similar(self.TEST_URL, num_results=2)

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 20_000

    async def test_async_returns_no_contents_when_false(self, async_exa):
        """Verify async find_similar() returns no contents when contents=False."""
        response = await async_exa.find_similar(
            self.TEST_URL, contents=False, num_results=2
        )

        assert len(response.results) > 0
        sample_result = response.results[0]
        assert sample_result.text is None
        assert sample_result.summary is None
