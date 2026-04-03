"""Structured-output round-trip example for answer, summaries, and deep search."""

import os
from typing import List, Optional

from pydantic import BaseModel, Field

from exa_py import Exa


class AnswerSchema(BaseModel):
    """Structured answer shape for a quick market overview."""

    company_name: str = Field(description="Company being described")
    core_focus: str = Field(description="Primary product or market focus")
    notable_signals: List[str] = Field(description="Most important recent signals")


class SummarySchema(BaseModel):
    """Structured page summary shape for documentation pages."""

    page_topic: str = Field(description="Main topic of the page")
    intended_audience: Optional[str] = Field(
        default=None, description="Who the page is written for"
    )
    key_takeaways: List[str] = Field(description="Most useful takeaways from the page")


class DeepSearchSchema(BaseModel):
    """Structured deep-search synthesis for research trade-off analysis."""

    recommendation: str = Field(description="Recommended path based on the evidence")
    supporting_points: List[str] = Field(
        description="Main arguments supporting the recommendation"
    )
    tradeoffs: List[str] = Field(description="Important tradeoffs to consider")


def main() -> None:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY environment variable not set!")

    base_url = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")
    exa = Exa(api_key, base_url)

    answer_response = exa.answer(
        "Summarize what Exa does for AI teams in a structured format.",
        output_schema=AnswerSchema,
        model="exa",
    )
    print("Answer parsed_output:")
    print(answer_response.parsed_output.model_dump() if answer_response.parsed_output else None)

    contents_response = exa.get_contents(
        ["https://docs.exa.ai"],
        summary={"schema": SummarySchema},
    )
    first_summary = contents_response.results[0].parsed_summary
    print("\nContents parsed_summary:")
    print(first_summary.model_dump() if first_summary else None)

    deep_search_response = exa.search(
        "Compare retrieval augmented generation and fine-tuning for enterprise assistants.",
        type="deep",
        num_results=5,
        contents=False,
        output_schema=DeepSearchSchema,
    )
    parsed_deep_output = (
        deep_search_response.output.parsed_content
        if deep_search_response.output is not None
        else None
    )
    print("\nDeep search parsed_content:")
    print(parsed_deep_output.model_dump() if parsed_deep_output else None)


if __name__ == "__main__":
    main()
