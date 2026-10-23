"""Response values and variants exa-py does not list parse instead of raising.

Each case feeds a payload carrying a value or tag the SDK does not know and
checks it is kept. Payloads with a known tag are still validated against
their variant, and request models still reject values outside their list.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import TypeAdapter, ValidationError

from exa_py.agent.monitors.types import AgentMonitor, AgentMonitorChange
from exa_py.agent.types import AgentGroundingEntry, AgentUsage, CreateAgentRunParams
from exa_py.monitors.types import SearchMonitor, SearchMonitorRun, UpdateSearchMonitorParams
from exa_py.research.models import (
    ResearchDto,
    ResearchEvent,
    ResearchPlanOperationEvent,
    ResearchRunningDto,
    ResearchOutputEvent,
    ResearchUnknownDto,
    ResearchUnknownEvent,
    ResearchUnknownOperation,
    ResearchUnknownOutput,
)
from exa_py.websets.events.client import EventsClient
from exa_py.websets.types import (
    Event,
    ListEventsResponse,
    Monitor,
    MonitorBehaviorSearch,
    PreviewWebsetResponseEnrichment,
    UnknownEvent,
    UnknownMonitorBehavior,
    UnknownWebsetEntity,
    UnknownWebsetItemProperties,
    Webset,
    WebsetCompanyEntity,
    WebsetIdleEvent,
    WebsetItem,
    WebsetItemCompanyProperties,
    WebsetSearch,
)

NOW = "2026-01-01T00:00:00Z"


def _webset(**overrides):
    return {
        "id": "ws_1",
        "object": "webset",
        "status": "idle",
        "dashboardUrl": "https://websets.exa.ai/ws_1",
        "searches": [],
        "enrichments": [],
        "monitors": [],
        "createdAt": NOW,
        "updatedAt": NOW,
        **overrides,
    }


def _item(properties):
    return {
        "id": "item_1",
        "object": "webset_item",
        "source": "search",
        "sourceId": "search_1",
        "websetId": "ws_1",
        "properties": properties,
        "evaluations": [],
        "enrichments": [],
        "createdAt": NOW,
        "updatedAt": NOW,
    }


def _search(entity):
    return {
        "id": "search_1",
        "object": "webset_search",
        "websetId": "ws_1",
        "status": "completed",
        "query": "q",
        "entity": entity,
        "criteria": [],
        "count": 1,
        "progress": {"found": 1, "completion": 100, "analyzed": 1},
        "createdAt": NOW,
        "updatedAt": NOW,
    }


class TestWebsets:
    def test_unknown_event_type_is_kept_in_a_list(self):
        new_event = {"id": "ev_2", "object": "event", "type": "webset.archived", "data": {"id": "ws_1"}, "createdAt": NOW}
        known_event = {"id": "ev_1", "object": "event", "type": "webset.idle", "data": _webset(), "createdAt": NOW}
        page = ListEventsResponse.model_validate({"data": [known_event, new_event], "hasMore": False, "nextCursor": None})
        assert isinstance(page.data[0], WebsetIdleEvent)
        assert isinstance(page.data[1], UnknownEvent)
        assert page.data[1].type == "webset.archived"
        assert page.data[1].data == {"id": "ws_1"}
        assert page.data[1].created_at.year == 2026

    def test_known_event_type_with_a_broken_payload_still_raises(self):
        with pytest.raises(ValidationError):
            TypeAdapter(Event).validate_python({"id": "ev_1", "object": "event", "type": "webset.idle", "createdAt": NOW})

    def test_events_get_returns_an_unknown_event(self):
        client = MagicMock()
        events = EventsClient(client)
        events.request = MagicMock(return_value={"id": "ev_2", "object": "event", "type": "webset.archived", "data": {}, "createdAt": NOW})
        assert isinstance(events.get("ev_2"), UnknownEvent)

    def test_unknown_status_is_kept(self):
        assert Webset.model_validate(_webset(status="archived")).status == "archived"

    def test_known_status_is_the_plain_string(self):
        assert Webset.model_validate(_webset()).status == "idle"

    def test_unknown_item_properties_type_is_kept(self):
        item = WebsetItem.model_validate(
            _item({"type": "job_posting", "url": "https://jobs.example.com/1", "description": "A job", "title": "Engineer"})
        )
        assert isinstance(item.properties, UnknownWebsetItemProperties)
        assert item.properties.type == "job_posting"
        assert item.properties.description == "A job"
        assert str(item.properties.url) == "https://jobs.example.com/1"
        assert item.properties.title == "Engineer"

    def test_known_item_properties_type_parses_to_its_model(self):
        item = WebsetItem.model_validate(
            _item({"type": "company", "url": "https://exa.ai", "description": "d", "company": {"name": "Exa"}})
        )
        assert isinstance(item.properties, WebsetItemCompanyProperties)

    def test_unknown_entity_type_is_kept(self):
        search = WebsetSearch.model_validate(_search({"type": "job_posting"}))
        assert isinstance(search.entity, UnknownWebsetEntity)

    def test_known_entity_type_parses_to_its_model(self):
        assert isinstance(WebsetSearch.model_validate(_search({"type": "company"})).entity, WebsetCompanyEntity)

    def test_unknown_monitor_behavior_is_kept(self):
        monitor = Monitor.model_validate(
            {
                "id": "mon_1",
                "status": "enabled",
                "websetId": "ws_1",
                "cadence": {"cron": "0 0 * * *"},
                "behavior": {"type": "dedupe", "config": {"window": "7d"}},
                "metadata": {},
                "createdAt": NOW,
                "updatedAt": NOW,
            }
        )
        assert isinstance(monitor.behavior, UnknownMonitorBehavior)
        assert monitor.behavior.config == {"window": "7d"}

    def test_known_monitor_behavior_parses_to_its_model(self):
        monitor = Monitor.model_validate(
            {
                "id": "mon_1",
                "status": "enabled",
                "websetId": "ws_1",
                "cadence": {"cron": "0 0 * * *"},
                "behavior": {"type": "search", "config": {"count": 10}},
                "metadata": {},
                "createdAt": NOW,
                "updatedAt": NOW,
            }
        )
        assert isinstance(monitor.behavior, MonitorBehaviorSearch)

    def test_preview_enrichment_accepts_url_format(self):
        assert PreviewWebsetResponseEnrichment.model_validate({"description": "Website", "format": "url"}).format == "url"


class TestResearch:
    BASE = {"researchId": "r_1", "createdAt": 1, "instructions": "i"}

    def test_unknown_status_is_kept(self):
        research = TypeAdapter(ResearchDto).validate_python({**self.BASE, "status": "queued", "model": "exa-research-max"})
        assert isinstance(research, ResearchUnknownDto)
        assert research.status == "queued"
        assert research.model == "exa-research-max"

    def test_unknown_event_type_is_kept(self):
        event = TypeAdapter(ResearchEvent).validate_python({"eventType": "plan-revised", "researchId": "r_1", "createdAt": 1})
        assert isinstance(event, ResearchUnknownEvent)

    def test_unknown_operation_type_is_kept(self):
        event = ResearchPlanOperationEvent.model_validate(
            {
                "eventType": "plan-operation",
                "researchId": "r_1",
                "planId": "p_1",
                "operationId": "o_1",
                "createdAt": 1,
                "data": {"type": "browse", "url": "https://exa.ai"},
            }
        )
        assert isinstance(event.data, ResearchUnknownOperation)

    def test_unknown_output_type_is_kept(self):
        event = ResearchOutputEvent.model_validate(
            {"eventType": "research-output", "researchId": "r_1", "createdAt": 1, "output": {"outputType": "partial", "content": "c"}}
        )
        assert isinstance(event.output, ResearchUnknownOutput)

    def test_running_research_keeps_unknown_events(self):
        research = TypeAdapter(ResearchDto).validate_python(
            {**self.BASE, "status": "running", "events": [{"eventType": "plan-revised", "researchId": "r_1", "createdAt": 1}]}
        )
        assert isinstance(research, ResearchRunningDto)
        assert isinstance(research.events[0], ResearchUnknownEvent)


class TestMonitorsAndAgent:
    def test_agent_monitor_unknown_status_and_progress_state(self):
        monitor = AgentMonitor.model_validate(
            {
                "id": "am_1",
                "status": "paused",
                "cadence": "12h",
                "fields": [{"id": "f_1", "name": "price", "description": "Price", "mode": "on_demand"}],
                "entityCount": 0,
                "version": 1,
                "createdAt": NOW,
                "refresh": {"state": "queued"},
            }
        )
        assert monitor.status == "paused"
        assert monitor.refresh.state == "queued"
        assert monitor.fields[0].mode == "on_demand"

    def test_agent_monitor_unknown_change_type(self):
        change = AgentMonitorChange.model_validate(
            {
                "type": "content.corrected",
                "entity": {"id": "e_1"},
                "field": {"id": "f_1", "name": "price"},
                "content": {"value": "1", "updatedAt": NOW},
                "version": 2,
                "createdAt": NOW,
            }
        )
        assert change.type == "content.corrected"

    def test_agent_usage_keeps_whole_counts_as_int(self):
        usage = AgentUsage.model_validate({"searches": 3, "emails": 0, "phoneNumbers": 1.5})
        assert (usage.searches, usage.emails, usage.phone_numbers) == (3, 0, 1.5)
        assert type(usage.searches) is int and type(usage.emails) is int
        assert type(usage.phone_numbers) is float
        assert list(range(usage.searches)) == [0, 1, 2]

    def test_agent_grounding_unknown_confidence(self):
        assert AgentGroundingEntry.model_validate({"field": "f", "citations": [], "confidence": "very_high"}).confidence == "very_high"

    def test_search_monitor_unknown_status_trigger_and_webhook_event(self):
        monitor = SearchMonitor.model_validate(
            {
                "id": "sm_1",
                "status": "archived",
                "search": {"query": "q", "contents": {"livecrawl": "smart", "text": {"verbosity": "minimal"}}},
                "trigger": {"type": "cron", "period": "0 0 * * *"},
                "webhook": {"url": "https://example.com/hook", "events": ["monitor.run.failed"]},
                "createdAt": NOW,
                "updatedAt": NOW,
            }
        )
        assert monitor.status == "archived"
        assert monitor.trigger.type == "cron"
        assert monitor.webhook.events == ["monitor.run.failed"]

    def test_search_monitor_run_unknown_status(self):
        run = SearchMonitorRun.model_validate(
            {"id": "r_1", "monitorId": "sm_1", "status": "skipped", "createdAt": NOW, "updatedAt": NOW}
        )
        assert run.status == "skipped"


class TestRequestModelsStayClosed:
    def test_agent_run_effort(self):
        with pytest.raises(ValidationError):
            CreateAgentRunParams.model_validate({"query": "q", "effort": "extreme"})

    def test_search_monitor_status_update(self):
        with pytest.raises(ValidationError):
            UpdateSearchMonitorParams.model_validate({"status": "archived"})
