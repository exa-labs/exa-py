"""
Pydantic Answer Example for Exa

This example demonstrates how to use Pydantic models with the answer() and stream_answer()
endpoints for structured response generation.
"""

import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field
from exa_py import Exa, AsyncExa

# Set up API key
EXA_API_KEY = os.environ.get("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = Exa(EXA_API_KEY)
async_exa = AsyncExa(EXA_API_KEY)

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


# ===============================================
# Example Functions
# ===============================================


def compare_technologies():
    """Compare different technologies using structured output."""
    print("🔬 TECHNOLOGY COMPARISON")
    print("=" * 50)

    response = exa.answer(
        "Compare React vs Vue.js vs Angular for web development. Include pros, cons, and recommendations.",
        output_schema=ComparisonAnalysis,
        model="exa-pro",
    )

    print(f"Answer type: {type(response.answer)}")

    if isinstance(response.answer, dict):
        comparison = response.answer
        print(f"\n📊 {comparison['title']}")
        print(f"\n📝 Executive Summary:")
        print(f"   {comparison['executive_summary']}")

        print(f"\n🎯 Items Compared: {', '.join(comparison['items_compared'])}")

        print(f"\n🔍 Key Differences:")
        for diff in comparison["key_differences"]:
            print(f"   • {diff}")

        if comparison.get("similarities"):
            print(f"\n🤝 Similarities:")
            for sim in comparison["similarities"]:
                print(f"   • {sim}")

        if comparison.get("winner"):
            print(f"\n🏆 Winner: {comparison['winner']}")
            print(f"   Reasoning: {comparison['reasoning']}")

        print(f"\n💡 Recommendation:")
        print(f"   {comparison['recommendation']}")
    else:
        print(f"Answer: {response.answer}")

    print(f"\n📚 Sources used: {len(response.citations)}")


def explain_technical_concept():
    """Get a technical explanation with structured output."""
    print("\n\n🧠 TECHNICAL EXPLANATION")
    print("=" * 50)

    response = exa.answer(
        "Explain quantum computing in detail, including both simple and technical explanations",
        output_schema=TechnicalExplanation,
        model="exa-pro",
    )

    if isinstance(response.answer, dict):
        explanation = response.answer
        print(f"\n📖 Topic: {explanation['topic']}")

        print(f"\n🔤 Simple Explanation:")
        print(f"   {explanation['simple_explanation']}")

        print(f"\n🔬 Technical Details:")
        print(f"   {explanation['technical_details']}")

        print(f"\n🎯 Key Concepts:")
        for concept in explanation["key_concepts"]:
            print(f"   • {concept}")

        if explanation.get("real_world_applications"):
            print(f"\n🌍 Real-World Applications:")
            for app in explanation["real_world_applications"]:
                print(f"   • {app}")
    else:
        print(f"Answer: {response.answer}")


def research_market():
    """Conduct market research with structured output."""
    print("\n\n📈 MARKET RESEARCH")
    print("=" * 50)

    response = exa.answer(
        "Analyze the electric vehicle market, including size, growth, key players, trends, and outlook",
        output_schema=MarketResearch,
        model="exa-pro",
    )

    if isinstance(response.answer, dict):
        research = response.answer
        print(f"\n🏢 Market: {research['market_name']}")

        if research.get("market_size"):
            print(f"💰 Size: {research['market_size']}")
        if research.get("growth_rate"):
            print(f"📈 Growth Rate: {research['growth_rate']}")

        print(f"\n🏆 Key Players:")
        for player in research["key_players"]:
            print(f"   • {player}")

        print(f"\n📊 Market Trends:")
        for trend in research["market_trends"]:
            print(f"   • {trend}")

        print(f"\n🎯 Opportunities:")
        for opp in research["opportunities"]:
            print(f"   • {opp}")

        print(f"\n⚠️ Challenges:")
        for challenge in research["challenges"]:
            print(f"   • {challenge}")

        print(f"\n🔮 Outlook:")
        print(f"   {research['outlook']}")
    else:
        print(f"Answer: {response.answer}")


async def stream_structured_analysis():
    """Stream a comprehensive analysis with structured output."""
    print("\n\n🌊 STREAMING STRUCTURED ANALYSIS")
    print("=" * 50)

    stream_response = await async_exa.stream_answer(
        "Provide a comprehensive analysis of artificial intelligence's impact on healthcare",
        output_schema=ComprehensiveAnalysis,
        model="exa-pro",
    )

    print("🔄 Streaming response...")
    full_content = ""

    async for chunk in stream_response:
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content

    print("\n\n" + "=" * 50)
    print("📋 STREAM COMPLETE - Attempting to parse structured data...")

    # Try to parse the accumulated content as JSON
    try:
        if full_content.strip():
            # Look for JSON in the content
            import re

            json_match = re.search(r"\{.*\}", full_content, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
                print(f"\n✅ Successfully parsed structured data!")
                print(f"📖 Topic: {analysis_data.get('topic', 'N/A')}")
                print(f"🎯 Confidence: {analysis_data.get('confidence_level', 'N/A')}")

                if analysis_data.get("key_points"):
                    print(f"\n📌 Key Points:")
                    for point in analysis_data["key_points"][:3]:
                        print(f"   • {point}")
            else:
                print("⚠️ No JSON structure found in streamed response")
    except json.JSONDecodeError as e:
        print(f"⚠️ Could not parse JSON from streamed content: {e}")
    except Exception as e:
        print(f"⚠️ Error processing stream: {e}")


def demonstrate_dict_fallback():
    """Show that regular dict schemas still work (backward compatibility)."""
    print("\n\n🔄 BACKWARD COMPATIBILITY TEST")
    print("=" * 50)

    # Use a regular dict schema (old approach)
    dict_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Brief summary of the topic"},
            "pros": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of advantages",
            },
            "cons": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of disadvantages",
            },
        },
        "required": ["summary"],
    }

    response = exa.answer(
        "What are the pros and cons of remote work?",
        output_schema=dict_schema,  # Regular dict - should still work
        model="exa",
    )

    print("✅ Dict schema still works! (Backward compatibility confirmed)")
    if isinstance(response.answer, dict):
        print(f"📝 Summary: {response.answer.get('summary', 'N/A')}")
        if response.answer.get("pros"):
            print(f"✅ Pros: {', '.join(response.answer['pros'][:2])}")
        if response.answer.get("cons"):
            print(f"❌ Cons: {', '.join(response.answer['cons'][:2])}")
    else:
        print(f"Answer: {response.answer}")


# ===============================================
# Main Execution
# ===============================================


async def main():
    print("🚀 Pydantic Answer Examples with Exa")
    print("Demonstrating structured output generation with answer endpoints")
    print("=" * 60)

    try:
        # Sync examples
        compare_technologies()
        explain_technical_concept()
        research_market()
        demonstrate_dict_fallback()

        # Async streaming example
        await stream_structured_analysis()

        print(f"\n{'=' * 60}")
        print("✅ All examples completed successfully!")
        print("\n💡 Key Benefits of Pydantic with Answer endpoints:")
        print("  • Structured response generation")
        print("  • Type-safe output parsing")
        print("  • Consistent data formats")
        print("  • Better integration with downstream processing")
        print("  • Automatic validation of AI responses")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
