"""Compatibility tests for deprecated find_similar() contents behavior.

New code should use search() instead.
"""

import pytest


def first_result_or_skip(response):
    if len(response.results) == 0:
        pytest.skip("Deprecated find_similar returned no live matches for fixture URL")
    return response.results[0]


def summary_or_skip(result):
    if not result.summary or len(result.summary) <= 10:
        pytest.skip("Deprecated find_similar returned no live summary for fixture URL")
    return result.summary


class TestFindSimilarContentsOptions:
    """Compatibility suite for deprecated find_similar() contents behavior."""

    TEST_URL = "https://en.wikipedia.org/wiki/Ant"

    def test_defaults_to_text_contents_with_10k_max_characters(self, exa):
        """Verify deprecated find_similar() returns default text contents."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(self.TEST_URL, num_results=2)

        sample_result = first_result_or_skip(response)
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 10_000

    def test_returns_no_contents_when_explicitly_false(self, exa):
        """Verify deprecated find_similar() returns no contents when contents=False."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(self.TEST_URL, contents=False, num_results=2)

        sample_result = first_result_or_skip(response)
        assert sample_result.text is None
        assert sample_result.summary is None

    def test_returns_text_contents_when_explicitly_requested(self, exa):
        """Verify deprecated find_similar() returns text when explicitly requested."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(
                self.TEST_URL, contents={"text": True}, num_results=2
            )

        sample_result = first_result_or_skip(response)
        assert sample_result.text is not None
        assert len(sample_result.text) > 100

    def test_returns_text_with_custom_max_characters(self, exa):
        """Verify deprecated find_similar() respects custom maxCharacters."""
        max_chars = 500
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(
                self.TEST_URL,
                contents={"text": {"max_characters": max_chars}},
                num_results=2,
            )

        sample_result = first_result_or_skip(response)
        assert sample_result.text is not None
        assert len(sample_result.text) <= max_chars

    @pytest.mark.timeout(15)
    def test_returns_summary_when_requested(self, exa):
        """Verify deprecated find_similar() returns summary when requested."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(
                self.TEST_URL, contents={"summary": True}, num_results=2
            )

        sample_result = first_result_or_skip(response)
        summary_or_skip(sample_result)
        assert sample_result.text is None

    @pytest.mark.timeout(20)
    def test_returns_both_text_and_summary(self, exa):
        """Verify deprecated find_similar() can return both text and summary."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(
                self.TEST_URL,
                contents={"text": {"max_characters": 1000}, "summary": True},
                num_results=2,
            )

        sample_result = first_result_or_skip(response)
        assert sample_result.text is not None
        assert len(sample_result.text) > 100
        assert len(sample_result.text) <= 1000
        summary_or_skip(sample_result)

    def test_defaults_to_text_when_passing_other_options(self, exa):
        """Verify deprecated find_similar() defaults to text with other options."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = exa.find_similar(
                self.TEST_URL, num_results=3, exclude_source_domain=True
            )

        if len(response.results) == 0:
            pytest.skip("Deprecated find_similar returned no live matches for fixture URL")
        assert len(response.results) == 3
        sample_result = response.results[0]
        assert sample_result.text is not None
        assert len(sample_result.text) > 100


@pytest.mark.asyncio
class TestAsyncFindSimilarContentsOptions:
    """Compatibility suite for deprecated async find_similar() contents behavior."""

    TEST_URL = "https://en.wikipedia.org/wiki/Ant"

    async def test_async_defaults_to_text_contents(self, async_exa):
        """Verify deprecated async find_similar() returns text contents by default."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = await async_exa.find_similar(self.TEST_URL, num_results=2)

        sample_result = first_result_or_skip(response)
        assert sample_result.text is not None
        assert len(sample_result.text) > 1000
        assert len(sample_result.text) <= 10_000

    async def test_async_returns_no_contents_when_false(self, async_exa):
        """Verify deprecated async find_similar() returns no contents when contents=False."""
        with pytest.warns(DeprecationWarning, match="find_similar"):
            response = await async_exa.find_similar(
                self.TEST_URL, contents=False, num_results=2
            )

        sample_result = first_result_or_skip(response)
        assert sample_result.text is None
        assert sample_result.summary is None
