"""
Unit tests for Entity types in search results.

Tests verify that entity dataclasses are correctly structured
for company and person category searches.
"""

import pytest

from exa_py.api import (
    Entity,
    CompanyEntity,
    PersonEntity,
    EntityCompanyProperties,
    EntityPersonProperties,
    EntityCompanyPropertiesWorkforce,
    EntityCompanyPropertiesHeadquarters,
    EntityCompanyPropertiesFinancials,
    EntityCompanyPropertiesFundingRound,
    EntityCompanyPropertiesWebTraffic,
    EntityDateRange,
    EntityPersonPropertiesCompanyRef,
    EntityPersonPropertiesWorkHistoryEntry,
    Result,
    _Result,
)


class TestEntityCompanyPropertiesWorkforce:
    def test_workforce_with_total(self):
        workforce = EntityCompanyPropertiesWorkforce(total=500)
        assert workforce.total == 500

    def test_workforce_with_none(self):
        workforce = EntityCompanyPropertiesWorkforce()
        assert workforce.total is None


class TestEntityCompanyPropertiesHeadquarters:
    def test_headquarters_full(self):
        hq = EntityCompanyPropertiesHeadquarters(
            address="123 Main St",
            city="San Francisco",
            postal_code="94105",
            country="US",
        )
        assert hq.address == "123 Main St"
        assert hq.city == "San Francisco"
        assert hq.postal_code == "94105"
        assert hq.country == "US"

    def test_headquarters_partial(self):
        hq = EntityCompanyPropertiesHeadquarters(city="New York")
        assert hq.city == "New York"
        assert hq.address is None
        assert hq.postal_code is None


class TestEntityCompanyPropertiesFundingRound:
    def test_funding_round_full(self):
        round = EntityCompanyPropertiesFundingRound(
            name="Series B",
            date="2023-06-15",
            amount=50000000,
        )
        assert round.name == "Series B"
        assert round.date == "2023-06-15"
        assert round.amount == 50000000

    def test_funding_round_empty(self):
        round = EntityCompanyPropertiesFundingRound()
        assert round.name is None
        assert round.date is None
        assert round.amount is None


class TestEntityCompanyPropertiesFinancials:
    def test_financials_full(self):
        financials = EntityCompanyPropertiesFinancials(
            revenue_annual=1000000000,
            funding_total=500000000,
        )
        assert financials.revenue_annual == 1000000000
        assert financials.funding_total == 500000000

    def test_financials_with_latest_round(self):
        financials = EntityCompanyPropertiesFinancials(
            funding_total=500000000,
            funding_latest_round=EntityCompanyPropertiesFundingRound(
                name="Series B",
                date="2023-06-15",
                amount=50000000,
            ),
        )
        assert financials.funding_total == 500000000
        assert financials.funding_latest_round is not None
        assert financials.funding_latest_round.name == "Series B"
        assert financials.funding_latest_round.amount == 50000000

    def test_financials_empty(self):
        financials = EntityCompanyPropertiesFinancials()
        assert financials.revenue_annual is None
        assert financials.funding_total is None
        assert financials.funding_latest_round is None


class TestEntityCompanyPropertiesWebTraffic:
    def test_web_traffic_with_visits(self):
        web_traffic = EntityCompanyPropertiesWebTraffic(visits_monthly=266306714)
        assert web_traffic.visits_monthly == 266306714

    def test_web_traffic_empty(self):
        web_traffic = EntityCompanyPropertiesWebTraffic()
        assert web_traffic.visits_monthly is None


class TestEntityCompanyProperties:
    def test_company_properties_full(self):
        props = EntityCompanyProperties(
            name="Exa",
            founded_year=2022,
            description="AI-powered search engine",
            workforce=EntityCompanyPropertiesWorkforce(total=50),
            headquarters=EntityCompanyPropertiesHeadquarters(city="San Francisco"),
            financials=EntityCompanyPropertiesFinancials(funding_total=50000000),
            web_traffic=EntityCompanyPropertiesWebTraffic(visits_monthly=266306714),
        )
        assert props.name == "Exa"
        assert props.founded_year == 2022
        assert props.workforce.total == 50
        assert props.headquarters.city == "San Francisco"
        assert props.financials.funding_total == 50000000
        assert props.web_traffic.visits_monthly == 266306714

    def test_company_properties_minimal(self):
        props = EntityCompanyProperties(name="Unknown Corp")
        assert props.name == "Unknown Corp"
        assert props.founded_year is None
        assert props.workforce is None
        assert props.web_traffic is None


class TestEntityDateRange:
    def test_date_range_full(self):
        dates = EntityDateRange(from_date="2020-01-15", to_date="2023-06-30")
        assert dates.from_date == "2020-01-15"
        assert dates.to_date == "2023-06-30"

    def test_date_range_open_ended(self):
        dates = EntityDateRange(from_date="2020-01-15")
        assert dates.from_date == "2020-01-15"
        assert dates.to_date is None


class TestEntityPersonPropertiesCompanyRef:
    def test_company_ref_full(self):
        ref = EntityPersonPropertiesCompanyRef(
            id="https://exa.ai/library/company/exa",
            name="Exa",
        )
        assert ref.id == "https://exa.ai/library/company/exa"
        assert ref.name == "Exa"

    def test_company_ref_name_only(self):
        ref = EntityPersonPropertiesCompanyRef(name="Startup Inc")
        assert ref.id is None
        assert ref.name == "Startup Inc"


class TestEntityPersonPropertiesWorkHistoryEntry:
    def test_work_history_entry_full(self):
        entry = EntityPersonPropertiesWorkHistoryEntry(
            title="Software Engineer",
            location="San Francisco, CA",
            dates=EntityDateRange(from_date="2020-01-15", to_date="2023-06-30"),
            company=EntityPersonPropertiesCompanyRef(id="exa-id", name="Exa"),
        )
        assert entry.title == "Software Engineer"
        assert entry.location == "San Francisco, CA"
        assert entry.dates.from_date == "2020-01-15"
        assert entry.company.name == "Exa"

    def test_work_history_entry_minimal(self):
        entry = EntityPersonPropertiesWorkHistoryEntry(title="Developer")
        assert entry.title == "Developer"
        assert entry.location is None
        assert entry.dates is None
        assert entry.company is None


class TestEntityPersonProperties:
    def test_person_properties_with_work_history(self):
        props = EntityPersonProperties(
            name="John Doe",
            location="San Francisco, CA",
            work_history=[
                EntityPersonPropertiesWorkHistoryEntry(
                    title="Software Engineer",
                    company=EntityPersonPropertiesCompanyRef(name="Exa"),
                ),
                EntityPersonPropertiesWorkHistoryEntry(
                    title="Junior Developer",
                    company=EntityPersonPropertiesCompanyRef(name="Startup Inc"),
                ),
            ],
        )
        assert props.name == "John Doe"
        assert props.location == "San Francisco, CA"
        assert len(props.work_history) == 2
        assert props.work_history[0].title == "Software Engineer"

    def test_person_properties_empty_history(self):
        props = EntityPersonProperties(name="Jane Doe", work_history=[])
        assert props.name == "Jane Doe"
        assert props.work_history == []


class TestCompanyEntity:
    def test_company_entity_full(self):
        entity = CompanyEntity(
            id="https://exa.ai/library/company/exa",
            type="company",
            version=1,
            properties=EntityCompanyProperties(
                name="Exa",
                founded_year=2022,
                description="AI-powered search engine",
            ),
        )
        assert entity.id == "https://exa.ai/library/company/exa"
        assert entity.type == "company"
        assert entity.version == 1
        assert entity.properties.name == "Exa"


class TestPersonEntity:
    def test_person_entity_full(self):
        entity = PersonEntity(
            id="https://exa.ai/library/person/john-doe",
            type="person",
            version=1,
            properties=EntityPersonProperties(
                name="John Doe",
                location="San Francisco, CA",
            ),
        )
        assert entity.id == "https://exa.ai/library/person/john-doe"
        assert entity.type == "person"
        assert entity.version == 1
        assert entity.properties.name == "John Doe"


class TestResultWithEntities:
    def test_result_with_entities(self):
        entities = [
            CompanyEntity(
                id="https://exa.ai/library/company/exa",
                type="company",
                version=1,
                properties=EntityCompanyProperties(name="Exa"),
            )
        ]
        result = Result(
            url="https://exa.ai",
            id="doc-123",
            title="Exa - AI Search Engine",
            entities=entities,
        )
        assert result.entities is not None
        assert len(result.entities) == 1
        assert result.entities[0].type == "company"
        assert result.entities[0].properties.name == "Exa"

    def test_result_without_entities(self):
        result = Result(
            url="https://example.com",
            id="doc-456",
            title="Some Article",
        )
        assert result.entities is None

    def test_result_str_includes_entities(self):
        entities = [
            CompanyEntity(
                id="exa-id",
                type="company",
                version=1,
                properties=EntityCompanyProperties(name="Exa"),
            )
        ]
        result = _Result(
            url="https://exa.ai",
            id="doc-123",
            entities=entities,
        )
        result_str = str(result)
        assert "Entities:" in result_str
        assert "[company] Exa" in result_str

    def test_result_str_without_entities(self):
        result = _Result(
            url="https://example.com",
            id="doc-456",
        )
        result_str = str(result)
        assert "Entities:" not in result_str
