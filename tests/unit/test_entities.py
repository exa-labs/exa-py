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
    EntityWorkforce,
    EntityHeadquarters,
    EntityFinancials,
    EntityDateRange,
    EntityCompanyRef,
    EntityWorkHistoryEntry,
    Result,
    _Result,
)


class TestEntityWorkforce:
    def test_workforce_with_total(self):
        workforce = EntityWorkforce(total=500)
        assert workforce.total == 500

    def test_workforce_with_none(self):
        workforce = EntityWorkforce()
        assert workforce.total is None


class TestEntityHeadquarters:
    def test_headquarters_full(self):
        hq = EntityHeadquarters(
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
        hq = EntityHeadquarters(city="New York")
        assert hq.city == "New York"
        assert hq.address is None
        assert hq.postal_code is None


class TestEntityFinancials:
    def test_financials_full(self):
        financials = EntityFinancials(
            revenue_annual=1000000000,
            funding_total=500000000,
        )
        assert financials.revenue_annual == 1000000000
        assert financials.funding_total == 500000000

    def test_financials_empty(self):
        financials = EntityFinancials()
        assert financials.revenue_annual is None
        assert financials.funding_total is None


class TestEntityCompanyProperties:
    def test_company_properties_full(self):
        props = EntityCompanyProperties(
            name="Exa",
            founded_year=2022,
            description="AI-powered search engine",
            workforce=EntityWorkforce(total=50),
            headquarters=EntityHeadquarters(city="San Francisco"),
            financials=EntityFinancials(funding_total=50000000),
        )
        assert props.name == "Exa"
        assert props.founded_year == 2022
        assert props.workforce.total == 50
        assert props.headquarters.city == "San Francisco"
        assert props.financials.funding_total == 50000000

    def test_company_properties_minimal(self):
        props = EntityCompanyProperties(name="Unknown Corp")
        assert props.name == "Unknown Corp"
        assert props.founded_year is None
        assert props.workforce is None


class TestEntityDateRange:
    def test_date_range_full(self):
        dates = EntityDateRange(from_date="2020-01-15", to="2023-06-30")
        assert dates.from_date == "2020-01-15"
        assert dates.to == "2023-06-30"

    def test_date_range_open_ended(self):
        dates = EntityDateRange(from_date="2020-01-15")
        assert dates.from_date == "2020-01-15"
        assert dates.to is None


class TestEntityCompanyRef:
    def test_company_ref_full(self):
        ref = EntityCompanyRef(
            id="https://exa.ai/library/company/exa",
            name="Exa",
        )
        assert ref.id == "https://exa.ai/library/company/exa"
        assert ref.name == "Exa"

    def test_company_ref_name_only(self):
        ref = EntityCompanyRef(name="Startup Inc")
        assert ref.id is None
        assert ref.name == "Startup Inc"


class TestEntityWorkHistoryEntry:
    def test_work_history_entry_full(self):
        entry = EntityWorkHistoryEntry(
            title="Software Engineer",
            location="San Francisco, CA",
            dates=EntityDateRange(from_date="2020-01-15", to="2023-06-30"),
            company=EntityCompanyRef(id="exa-id", name="Exa"),
        )
        assert entry.title == "Software Engineer"
        assert entry.location == "San Francisco, CA"
        assert entry.dates.from_date == "2020-01-15"
        assert entry.company.name == "Exa"

    def test_work_history_entry_minimal(self):
        entry = EntityWorkHistoryEntry(title="Developer")
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
                EntityWorkHistoryEntry(
                    title="Software Engineer",
                    company=EntityCompanyRef(name="Exa"),
                ),
                EntityWorkHistoryEntry(
                    title="Junior Developer",
                    company=EntityCompanyRef(name="Startup Inc"),
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

    def test_result_str_without_entities(self):
        result = _Result(
            url="https://example.com",
            id="doc-456",
        )
        result_str = str(result)
        assert "Entities:" not in result_str
