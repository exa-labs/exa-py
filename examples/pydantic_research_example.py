"""
Pydantic Research Example for Exa

This example demonstrates how to use Pydantic models with the research endpoint
for comprehensive analysis with parallelizable research tasks.
"""

import os
import json
from typing import List, Optional

from pydantic import BaseModel, Field
from exa_py import Exa

# Set up API key
EXA_API_KEY = os.environ.get("EXA_API_KEY")
if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")
EXA_BASE_URL = os.environ.get("EXA_BASE_URL", "https://api.exa.ai")

exa = Exa(EXA_API_KEY, EXA_BASE_URL)

# ===============================================
# Pydantic Models for Research Analysis
# ===============================================


class TechnologyInfo(BaseModel):
    """Information about a specific technology."""

    name: str = Field(description="Name of the technology")
    description: str = Field(description="Brief description of what it does")
    maturity_level: Optional[str] = Field(
        default=None, description="How mature/established the technology is"
    )
    key_players: Optional[List[str]] = Field(
        default=None, description="Companies or organizations leading this technology"
    )


class CompanyProfile(BaseModel):
    """Profile of a company."""

    name: str = Field(description="Company name")
    industry: str = Field(description="Primary industry")
    funding_amount: Optional[str] = Field(
        default=None, description="Latest funding amount if available"
    )
    notable_achievements: Optional[List[str]] = Field(
        default=None, description="Key achievements or milestones"
    )


class ResearchInsight(BaseModel):
    """Research insight or finding."""

    title: str = Field(description="Title of the research or insight")
    summary: str = Field(description="Brief summary of the finding")
    impact: Optional[str] = Field(
        default=None, description="Potential impact or significance"
    )


class TechnologyLandscape(BaseModel):
    """Comprehensive technology landscape analysis with parallelizable research areas."""

    emerging_technologies: List[TechnologyInfo] = Field(
        description="List of emerging technologies in the field"
    )
    market_leaders: List[CompanyProfile] = Field(
        description="Leading companies in the market"
    )
    investment_trends: List[ResearchInsight] = Field(
        description="Current investment and funding trends"
    )


class StartupEcosystem(BaseModel):
    """Startup ecosystem analysis with independent research dimensions."""

    top_startups: List[CompanyProfile] = Field(
        description="Most promising startups in the space"
    )
    funding_rounds: List[ResearchInsight] = Field(
        description="Recent significant funding rounds and deals"
    )
    industry_challenges: List[ResearchInsight] = Field(
        description="Key challenges facing the industry"
    )


class ResearchPaper(BaseModel):
    """Research paper information."""

    title: str = Field(description="Paper title")
    authors: List[str] = Field(description="List of authors")
    key_contribution: str = Field(description="Main contribution or finding")
    significance: Optional[str] = Field(
        default=None, description="Why this research is important"
    )


class Researcher(BaseModel):
    """Information about a researcher."""

    name: str = Field(description="Researcher's name")
    affiliation: str = Field(description="Institution or company")
    expertise: str = Field(description="Area of expertise")
    notable_work: Optional[List[str]] = Field(
        default=None, description="Notable research or contributions"
    )


class Application(BaseModel):
    """Commercial application information."""

    application_area: str = Field(description="Area where technology is applied")
    description: str = Field(description="How the technology is being used")
    companies: Optional[List[str]] = Field(
        default=None, description="Companies implementing this application"
    )


class AIResearchOverview(BaseModel):
    """AI research landscape with independent research dimensions."""

    breakthrough_papers: List[ResearchPaper] = Field(
        description="Recent breakthrough research papers"
    )
    leading_researchers: List[Researcher] = Field(
        description="Top researchers in the field"
    )
    commercial_applications: List[Application] = Field(
        description="Real-world applications and implementations"
    )


# ===============================================
# Example Functions
# ===============================================


def analyze_technology_landscape():
    """Analyze the quantum computing technology landscape."""
    print("Example 1: Technology Landscape Analysis")
    print("=" * 40)

    # Create the research task
    task = exa.research.create_task(
        instructions="quantum computing technology landscape, market leaders, and investment trends",
        output_schema=TechnologyLandscape,
        model="exa-research",
    )

    print(f"Created task {task.id}, polling for completion...")

    # Poll until completion
    final_task = exa.research.poll_task(task.id)

    # Check if we got structured output
    if isinstance(final_task.data, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{final_task.data}'")
        return

    analysis = final_task.data

    print("Emerging Technologies:")
    for tech in analysis["emerging_technologies"]:
        print(f"  • {tech['name']}: {tech['description']}")
        if tech.get("key_players"):
            print(f"    Key Players: {', '.join(tech['key_players'])}")

    print("\nMarket Leaders:")
    for company in analysis["market_leaders"]:
        print(f"  • {company['name']} ({company['industry']})")
        if company.get("funding_amount"):
            print(f"    Funding: {company['funding_amount']}")

    print("\nInvestment Trends:")
    for trend in analysis["investment_trends"]:
        print(f"  • {trend['title']}: {trend['summary']}")


def research_startup_ecosystem():
    """Research the fintech startup ecosystem."""
    print("\n\nExample 2: Startup Ecosystem Research")
    print("=" * 40)

    # Create the research task
    task = exa.research.create_task(
        instructions="fintech startup ecosystem, top companies, funding rounds, and industry challenges",
        output_schema=StartupEcosystem,
        model="exa-research",
    )

    print(f"Created task {task.id}, polling for completion...")

    # Poll until completion
    final_task = exa.research.poll_task(task.id)

    # Check if we got structured output
    if isinstance(final_task.data, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{final_task.data}'")
        return

    ecosystem = final_task.data

    print("Top Startups:")
    for startup in ecosystem["top_startups"]:
        print(f"  • {startup['name']} ({startup['industry']})")
        if startup.get("notable_achievements"):
            print(f"    Achievements: {', '.join(startup['notable_achievements'][:2])}")

    print("\nRecent Funding Rounds:")
    for funding in ecosystem["funding_rounds"]:
        print(f"  • {funding['title']}: {funding['summary']}")

    print("\nIndustry Challenges:")
    for challenge in ecosystem["industry_challenges"]:
        print(f"  • {challenge['title']}: {challenge['summary']}")


def explore_ai_research():
    """Explore the current AI research landscape."""
    print("\n\nExample 3: AI Research Overview")
    print("=" * 40)

    # Create the research task
    task = exa.research.create_task(
        instructions="artificial intelligence research breakthroughs, leading researchers, and commercial applications",
        output_schema=AIResearchOverview,
        model="exa-research",
    )

    print(f"Created task {task.id}, polling for completion...")

    # Poll until completion
    final_task = exa.research.poll_task(task.id)

    # Check if we got structured output
    if isinstance(final_task.data, str):
        print("ERROR: Expected structured output but received plain text:")
        print(f"'{final_task.data}'")
        return

    research = final_task.data

    print("Breakthrough Papers:")
    for paper in research["breakthrough_papers"]:
        authors_str = ", ".join(paper["authors"][:3])
        if len(paper["authors"]) > 3:
            authors_str += f" (and {len(paper['authors']) - 3} others)"
        print(f"  • {paper['title']}")
        print(f"    Authors: {authors_str}")
        print(f"    Contribution: {paper['key_contribution']}")

    print("\nLeading Researchers:")
    for researcher in research["leading_researchers"]:
        print(f"  • {researcher['name']} ({researcher['affiliation']})")
        print(f"    Expertise: {researcher['expertise']}")

    print("\nCommercial Applications:")
    for app in research["commercial_applications"]:
        print(f"  • {app['application_area']}: {app['description']}")
        if app.get("companies"):
            print(f"    Companies: {', '.join(app['companies'][:3])}")


# ===============================================
# Main Execution
# ===============================================


def main():
    print("Pydantic Research Examples with Exa")
    print("Comprehensive analysis using parallelizable research tasks")
    print("=" * 50)

    try:
        analyze_technology_landscape()
        research_startup_ecosystem()
        explore_ai_research()

        print("\n" + "=" * 50)
        print("Examples completed successfully!")

    except Exception as e:
        print("Error:", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
