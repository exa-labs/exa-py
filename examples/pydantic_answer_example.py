"""
Pydantic Answer Example for Exa

This example demonstrates how to use Pydantic models with the answer endpoint
for structured response generation.
"""

import os
import asyncio
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field
from exa_py import Exa, AsyncExa

# Set up API key
EXA_API_KEY = os.environ.get("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")
EXA_BASE_URL = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")

exa = Exa(EXA_API_KEY, EXA_BASE_URL)
async_exa = AsyncExa(EXA_API_KEY, EXA_BASE_URL)

# ===============================================
# Pydantic Models for Structured Answers
# ===============================================


class ConfidenceLevel(str, Enum):
    """Confidence level for the information."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Evidence(BaseModel):
    """Evidence supporting a claim or statement."""

    claim: str = Field(description="The specific claim or fact")
    source_description: str = Field(description="Brief description of the source")
    confidence: ConfidenceLevel = Field(description="Confidence level in this evidence")


class ComparisonAnalysis(BaseModel):
    """Structured comparison between two or more items."""

    title: str = Field(description="Title of the comparison")
    executive_summary: str = Field(description="Brief summary of the key differences")

    items_compared: List[str] = Field(description="List of items being compared")

    key_differences: List[str] = Field(description="Main differences between the items")
    similarities: Optional[List[str]] = Field(
        default=None, description="Key similarities"
    )

    winner: Optional[str] = Field(
        default=None, description="Which item is better overall, if applicable"
    )
    reasoning: Optional[str] = Field(
        default=None, description="Explanation for the winner choice"
    )

    recommendation: str = Field(description="Final recommendation or advice")


class TechnicalExplanation(BaseModel):
    """Model for technical explanations."""

    topic: str = Field(description="The technical topic being explained")
    simple_explanation: str = Field(description="Simple, non-technical explanation")
    technical_details: str = Field(description="More detailed technical explanation")

    key_concepts: List[str] = Field(description="Important concepts to understand")
    real_world_applications: Optional[List[str]] = Field(
        default=None, description="How this is used in practice"
    )

    prerequisites: Optional[List[str]] = Field(
        default=None, description="Background knowledge needed"
    )
    further_reading: Optional[List[str]] = Field(
        default=None, description="Resources for deeper learning"
    )


class MarketResearch(BaseModel):
    """Model for market research responses."""

    market_name: str = Field(description="Name of the market being analyzed")
    market_size: Optional[str] = Field(default=None, description="Size of the market")
    growth_rate: Optional[str] = Field(default=None, description="Market growth rate")

    key_players: List[str] = Field(description="Major companies in this market")
    market_trends: List[str] = Field(description="Current trends shaping the market")
    opportunities: List[str] = Field(description="Market opportunities")
    challenges: List[str] = Field(description="Market challenges")

    outlook: str = Field(description="Future outlook for the market")


class QuestionAnswerPair(BaseModel):
    """Q&A pair for complex topics."""

    question: str = Field(description="The question being answered")
    answer: str = Field(description="Detailed answer to the question")
    supporting_evidence: Optional[List[Evidence]] = Field(
        default=None, description="Evidence supporting the answer"
    )


class ComprehensiveAnalysis(BaseModel):
    """Comprehensive analysis format."""

    topic: str = Field(description="Main topic of analysis")
    overview: str = Field(description="High-level overview")

    key_points: List[str] = Field(description="Most important points")
    detailed_analysis: List[QuestionAnswerPair] = Field(
        description="Detailed Q&A analysis"
    )

    conclusion: str = Field(description="Final conclusion")
    confidence_level: ConfidenceLevel = Field(
        description="Overall confidence in the analysis"
    )


class SimpleComparison(BaseModel):
    """Simple comparison model using standard JSON schema approach."""

    summary: str = Field(description="Brief summary of the topic")
    pros: List[str] = Field(description="List of advantages")
    cons: List[str] = Field(description="List of disadvantages")


# ===============================================
# Example Functions
# ===============================================


def compare_technologies():
    """Compare different technologies using structured output."""
    print("Example 1: Technology Comparison")
    print("=" * 40)

    response = exa.answer(
        "Compare React vs Vue.js vs Angular for web development. Include pros, cons, and recommendations.",
        output_schema=ComparisonAnalysis,
        model="exa",
    )

    # Check if we got structured output
    if isinstance(response.answer, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{response.answer}'")
        return

    comparison = response.answer
    print("Title:", comparison["title"])
    print("\nExecutive Summary:")
    print(comparison["executive_summary"])

    print("\nItems Compared:", ", ".join(comparison["items_compared"]))

    print("\nKey Differences:")
    for diff in comparison["key_differences"]:
        print(f"  • {diff}")

    if comparison.get("similarities"):
        print("\nSimilarities:")
        for sim in comparison["similarities"]:
            print(f"  • {sim}")

    if comparison.get("winner"):
        print(f"\nRecommended Choice: {comparison['winner']}")
        print(f"Reasoning: {comparison['reasoning']}")

    print("\nFinal Recommendation:")
    print(comparison["recommendation"])

    print(f"\nSources: {len(response.citations)} citations")


def explain_technical_concept():
    """Get a technical explanation with structured output."""
    print("\n\nExample 2: Technical Explanation")
    print("=" * 40)

    response = exa.answer(
        "Explain quantum computing in detail, including both simple and technical explanations",
        output_schema=TechnicalExplanation,
        model="exa",
    )

    # Check if we got structured output
    if isinstance(response.answer, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{response.answer}'")
        return

    explanation = response.answer
    print("Topic:", explanation["topic"])

    print("\nSimple Explanation:")
    print(explanation["simple_explanation"])

    print("\nTechnical Details:")
    print(explanation["technical_details"])

    print("\nKey Concepts:")
    for concept in explanation["key_concepts"]:
        print(f"  • {concept}")

    if explanation.get("real_world_applications"):
        print("\nReal-World Applications:")
        for app in explanation["real_world_applications"]:
            print(f"  • {app}")


def research_market():
    """Conduct market research with structured output."""
    print("\n\nExample 3: Market Research")
    print("=" * 40)

    response = exa.answer(
        "Analyze the electric vehicle market, including size, growth, key players, trends, and outlook",
        output_schema=MarketResearch,
        model="exa",
    )

    # Check if we got structured output
    if isinstance(response.answer, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{response.answer}'")
        return

    research = response.answer
    print("Market:", research["market_name"])

    if research.get("market_size"):
        print("Size:", research["market_size"])
    if research.get("growth_rate"):
        print("Growth Rate:", research["growth_rate"])

    print("\nKey Players:")
    for player in research["key_players"]:
        print(f"  • {player}")

    print("\nMarket Trends:")
    for trend in research["market_trends"]:
        print(f"  • {trend}")

    print("\nOpportunities:")
    for opp in research["opportunities"]:
        print(f"  • {opp}")

    print("\nChallenges:")
    for challenge in research["challenges"]:
        print(f"  • {challenge}")

    print("\nOutlook:")
    print(research["outlook"])


def simple_structured_output():
    """Demonstrate structured output with a simpler Pydantic model."""
    print("\n\nExample 4: Simple Structured Output")
    print("=" * 40)

    response = exa.answer(
        "What are the pros and cons of remote work?",
        output_schema=SimpleComparison,
        model="exa",
    )

    # Check if we got structured output
    if isinstance(response.answer, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{response.answer}'")
        return

    result = response.answer
    print("Summary:", result["summary"])

    print("\nAdvantages:")
    for pro in result["pros"]:
        print(f"  • {pro}")

    print("\nDisadvantages:")
    for con in result["cons"]:
        print(f"  • {con}")


# ===============================================
# Main Execution
# ===============================================


async def main():
    print("Pydantic Answer Examples with Exa")
    print("Structured response generation using Pydantic models")
    print("=" * 50)

    try:
        compare_technologies()
        explain_technical_concept()
        research_market()
        simple_structured_output()

        print("\n" + "=" * 50)
        print("Examples completed successfully!")

    except Exception as e:
        print("Error:", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
