from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyUrl, Field, confloat, constr
from .core.base import ExaBaseModel


class CanceledReason(Enum):
    """
    The reason the search was canceled
    """

    webset_deleted = 'webset_deleted'
    webset_canceled = 'webset_canceled'


class CreateCriterionParameters(ExaBaseModel):
    description: constr(min_length=1)
    """
    The description of the criterion
    """


class CreateEnrichmentParameters(ExaBaseModel):
    description: constr(min_length=1)
    """
    Provide a description of the enrichment task you want to perform to each Webset Item.
    """
    format: Optional[Format] = None
    """
    Format of the enrichment response.

    We automatically select the best format based on the description. If you want to explicitly specify the format, you can do so here.
    """
    options: Optional[List[Option]] = Field(None, max_items=20, min_items=1)
    """
    When the format is options, the different options for the enrichment agent to choose from.
    """
    metadata: Optional[Dict[str, Any]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class CreateWebhookParameters(ExaBaseModel):
    events: List[EventType] = Field(..., max_items=12, min_items=1)
    """
    The events to trigger the webhook
    """
    url: AnyUrl
    """
    The URL to send the webhook to
    """
    metadata: Optional[Dict[str, Any]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class CreateWebsetParameters(ExaBaseModel):
    search: Search
    """
    Create initial search for the Webset.
    """
    enrichments: Optional[List[CreateEnrichmentParameters]] = Field(None, max_items=10)
    """
    Add Enrichments for the Webset.
    """
    external_id: Optional[str] = Field(None, alias='externalId')
    """
    The external identifier for the webset.

    You can use this to reference the Webset by your own internal identifiers.
    """
    metadata: Optional[Dict[str, Any]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class CreateWebsetSearchParameters(ExaBaseModel):
    count: confloat(ge=1.0)
    """
    Number of Items the Search will attempt to find.

    The actual number of Items found may be less than this number depending on the query complexity.
    """
    query: constr(min_length=1) = Field(
        ...,
        examples=[
            'Marketing agencies based in the US, that focus on consumer products. Get brands worked with and city'
        ],
    )
    """
    Query describing what you are looking for.

    Any URL provided will be crawled and used as context for the search.
    """
    entity: Optional[
        Union[
            WebsetCompanyEntity,
            WebsetPersonEntity,
            WebsetArticleEntity,
            WebsetResearchPaperEntity,
            WebsetCustomEntity,
        ]
    ] = None
    """
    Entity the Webset will return results for.

    It is not required to provide it, we automatically detect the entity from all the information provided in the query.
    """
    criteria: Optional[List[CreateCriterionParameters]] = Field(
        None, max_items=5, min_items=1
    )
    """
    Criteria every item is evaluated against.

    It's not required to provide your own criteria, we automatically detect the criteria from all the information provided in the query.
    """
    behaviour: Optional[WebsetSearchBehaviour] = Field(
        'override', title='WebsetSearchBehaviour'
    )
    """
    The behaviour of the Search when it is added to a Webset.

    - `override`: the search will reuse the existing Items found in the Webset and evaluate them against the new criteria. Any Items that don't match the new criteria will be discarded.
    """
    metadata: Optional[Dict[str, Any]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class Criterion(ExaBaseModel):
    description: constr(min_length=1)
    """
    The description of the criterion
    """
    success_rate: confloat(ge=0.0, le=100.0) = Field(..., alias='successRate')
    """
    Value between 0 and 100 representing the percentage of results that meet the criterion.
    """


class EnrichmentResult(ExaBaseModel):
    object: Literal['enrichment_result']
    format: WebsetEnrichmentFormat
    result: Optional[List[str]] = None
    """
    The result of the enrichment. None if the enrichment wasn't successful.
    """
    reasoning: Optional[str] = None
    """
    The reasoning for the result when an Agent is used.
    """
    references: List[Reference]
    """
    The references used to generate the result.
    """
    enrichment_id: str = Field(..., alias='enrichmentId')
    """
    The id of the Enrichment that generated the result
    """


class EventType(Enum):
    webset_created = 'webset.created'
    webset_deleted = 'webset.deleted'
    webset_paused = 'webset.paused'
    webset_idle = 'webset.idle'
    webset_search_created = 'webset.search.created'
    webset_search_canceled = 'webset.search.canceled'
    webset_search_completed = 'webset.search.completed'
    webset_search_updated = 'webset.search.updated'
    webset_export_created = 'webset.export.created'
    webset_export_completed = 'webset.export.completed'
    webset_item_created = 'webset.item.created'
    webset_item_enriched = 'webset.item.enriched'



class Format(Enum):
    """
    Format of the enrichment response.

    We automatically select the best format based on the description. If you want to explicitly specify the format, you can do so here.
    """

    text = 'text'
    date = 'date'
    number = 'number'
    options = 'options'
    email = 'email'
    phone = 'phone'


class ListEventsResponse(ExaBaseModel):
    data: List[
        Union[
            WebsetCreatedEvent,
            WebsetDeletedEvent,
            WebsetIdleEvent,
            WebsetPausedEvent,
            WebsetItemCreatedEvent,
            WebsetItemEnrichedEvent,
            WebsetSearchCreatedEvent,
            WebsetSearchUpdatedEvent,
            WebsetSearchCanceledEvent,
            WebsetSearchCompletedEvent,
        ]
    ] = Field(..., discriminator='type')
    """
    The list of events
    """
    has_more: bool = Field(..., alias='hasMore')
    """
    Whether there are more results to paginate through
    """
    next_cursor: Optional[str] = Field(..., alias='nextCursor')
    """
    The cursor to paginate through the next set of results
    """


class ListWebhookAttemptsResponse(ExaBaseModel):
    data: List[WebhookAttempt]
    """
    The list of webhook attempts
    """
    has_more: bool = Field(..., alias='hasMore')
    """
    Whether there are more results to paginate through
    """
    next_cursor: Optional[str] = Field(..., alias='nextCursor')
    """
    The cursor to paginate through the next set of results
    """


class ListWebhooksResponse(ExaBaseModel):
    data: List[Webhook]
    """
    The list of webhooks
    """
    has_more: bool = Field(..., alias='hasMore')
    """
    Whether there are more results to paginate through
    """
    next_cursor: Optional[str] = Field(..., alias='nextCursor')
    """
    The cursor to paginate through the next set of results
    """


class ListWebsetItemResponse(ExaBaseModel):
    data: List[WebsetItem]
    """
    The list of webset items
    """
    has_more: bool = Field(..., alias='hasMore')
    """
    Whether there are more Items to paginate through
    """
    next_cursor: Optional[str] = Field(..., alias='nextCursor')
    """
    The cursor to paginate through the next set of Items
    """


class ListWebsetsResponse(ExaBaseModel):
    data: List[Webset]
    """
    The list of websets
    """
    has_more: bool = Field(..., alias='hasMore')
    """
    Whether there are more results to paginate through
    """
    next_cursor: Optional[str] = Field(..., alias='nextCursor')
    """
    The cursor to paginate through the next set of results
    """


class Option(ExaBaseModel):
    label: str
    """
    The label of the option
    """


class Progress(ExaBaseModel):
    """
    The progress of the search
    """

    found: float
    """
    The number of results found so far
    """
    completion: confloat(ge=0.0, le=100.0)
    """
    The completion percentage of the search
    """


class Reference(ExaBaseModel):
    title: Optional[str] = None
    """
    The title of the reference
    """
    snippet: Optional[str] = None
    """
    The relevant snippet of the reference content
    """
    url: AnyUrl
    """
    The URL of the reference
    """


class Satisfied(Enum):
    """
    The satisfaction of the criterion
    """

    yes = 'yes'
    no = 'no'
    unclear = 'unclear'


class Search(ExaBaseModel):
    """
    Create initial search for the Webset.
    """

    query: constr(min_length=1) = Field(
        ...,
        examples=[
            'Marketing agencies based in the US, that focus on consumer products.'
        ],
    )
    """
    Your search query.

    Use this to describe what you are looking for.

    Any URL provided will be crawled and used as context for the search.
    """
    count: Optional[confloat(ge=1.0)] = 10
    """
    Number of Items the Webset will attempt to find.

    The actual number of Items found may be less than this number depending on the search complexity.
    """
    entity: Optional[
        Union[
            WebsetCompanyEntity,
            WebsetPersonEntity,
            WebsetArticleEntity,
            WebsetResearchPaperEntity,
            WebsetCustomEntity,
        ]
    ] = Field(None, discriminator='type')
    """
    Entity the Webset will return results for.

    It is not required to provide it, we automatically detect the entity from all the information provided in the query. Only use this when you need more fine control.
    """
    criteria: Optional[List[CreateCriterionParameters]] = Field(
        None, max_items=5, min_items=1
    )
    """
    Criteria every item is evaluated against.

    It's not required to provide your own criteria, we automatically detect the criteria from all the information provided in the query. Only use this when you need more fine control.
    """


class Source(Enum):
    """
    The source of the Item
    """

    search = 'search'


class UpdateWebhookParameters(ExaBaseModel):
    events: Optional[List[EventType]] = Field(None, max_items=12, min_items=1)
    """
    The events to trigger the webhook
    """
    url: Optional[AnyUrl] = None
    """
    The URL to send the webhook to
    """
    metadata: Optional[Dict[str, Any]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class UpdateWebsetRequest(ExaBaseModel):
    metadata: Optional[Dict[str, str]] = None
    """
    Set of key-value pairs you want to associate with this object.
    """


class Webhook(ExaBaseModel):
    id: str
    """
    The unique identifier for the webhook
    """
    object: Literal['webhook']
    status: WebhookStatus = Field(..., title='WebhookStatus')
    """
    The status of the webhook
    """
    events: List[EventType] = Field(..., min_items=1)
    """
    The events to trigger the webhook
    """
    url: AnyUrl
    """
    The URL to send the webhook to
    """
    secret: Optional[str] = None
    """
    The secret to verify the webhook signature. Only returned on Webhook creation.
    """
    metadata: Optional[Dict[str, Any]] = {}
    """
    The metadata of the webhook
    """
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the webhook was created
    """
    updated_at: datetime = Field(..., alias='updatedAt')
    """
    The date and time the webhook was last updated
    """


class WebhookAttempt(ExaBaseModel):
    id: str
    """
    The unique identifier for the webhook attempt
    """
    object: Literal['webhook_attempt']
    event_id: str = Field(..., alias='eventId')
    """
    The unique identifier for the event
    """
    event_type: EventType = Field(..., alias='eventType')
    """
    The type of event
    """
    webhook_id: str = Field(..., alias='webhookId')
    """
    The unique identifier for the webhook
    """
    url: str
    """
    The URL that was used during the attempt
    """
    successful: bool
    """
    Whether the attempt was successful
    """
    response_headers: Dict[str, Any] = Field(..., alias='responseHeaders')
    """
    The headers of the response
    """
    response_body: str = Field(..., alias='responseBody')
    """
    The body of the response
    """
    response_status_code: float = Field(..., alias='responseStatusCode')
    """
    The status code of the response
    """
    attempt: float
    """
    The attempt number of the webhook
    """
    attempted_at: datetime = Field(..., alias='attemptedAt')
    """
    The date and time the webhook attempt was made
    """


class WebhookStatus(Enum):
    """
    The status of the webhook
    """

    active = 'active'
    inactive = 'inactive'


class Webset(ExaBaseModel):
    id: str
    """
    The unique identifier for the webset
    """
    object: Literal['webset']
    status: WebsetStatus = Field(..., title='WebsetStatus')
    """
    The status of the webset
    """
    external_id: Optional[str] = Field(..., alias='externalId')
    """
    The external identifier for the webset
    """
    searches: List[WebsetSearch]
    """
    The searches that have been performed on the webset.
    """
    enrichments: List[WebsetEnrichment]
    """
    The Enrichments to apply to the Webset Items.
    """
    metadata: Optional[Dict[str, Any]] = {}
    """
    Set of key-value pairs you want to associate with this object.
    """
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the webset was created
    """
    updated_at: datetime = Field(..., alias='updatedAt')
    """
    The date and time the webset was updated
    """


class WebsetArticleEntity(ExaBaseModel):
    type: Literal['article']


class WebsetCompanyEntity(ExaBaseModel):
    type: Literal['company']


class WebsetCreatedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.created']
    data: Webset
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetCustomEntity(ExaBaseModel):
    type: Literal['custom']
    description: constr(min_length=2)
    """
    When you decide to use a custom entity, this is the description of the entity.

    The entity represents what type of results the Webset will return. For example, if you want results to be Job Postings, you might use "Job Postings" as the entity description.
    """


class WebsetDeletedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.deleted']
    data: Webset
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetEnrichment(ExaBaseModel):
    id: str
    """
    The unique identifier for the enrichment
    """
    object: Literal['webset_enrichment']
    status: WebsetEnrichmentStatus = Field(..., title='WebsetEnrichmentStatus')
    """
    The status of the enrichment
    """
    webset_id: str = Field(..., alias='websetId')
    """
    The unique identifier for the Webset this enrichment belongs to.
    """
    title: Optional[str] = None
    """
    The title of the enrichment.

    This will be automatically generated based on the description and format.
    """
    description: str
    """
    The description of the enrichment task provided during the creation of the enrichment.
    """
    format: Optional[WebsetEnrichmentFormat]
    """
    The format of the enrichment response.
    """
    options: Optional[List[WebsetEnrichmentOption]] = Field(
        ..., title='WebsetEnrichmentOptions'
    )
    """
    When the format is options, the different options for the enrichment agent to choose from.
    """
    instructions: Optional[str] = None
    """
    The instructions for the enrichment Agent.

    This will be automatically generated based on the description and format.
    """
    metadata: Optional[Dict[str, Any]] = {}
    """
    The metadata of the enrichment
    """
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the enrichment was created
    """
    updated_at: datetime = Field(..., alias='updatedAt')
    """
    The date and time the enrichment was updated
    """


class WebsetEnrichmentFormat(Enum):
    text = 'text'
    date = 'date'
    number = 'number'
    options = 'options'
    email = 'email'
    phone = 'phone'


class WebsetEnrichmentOption(Option):
    pass


class WebsetEnrichmentStatus(Enum):
    """
    The status of the enrichment
    """

    pending = 'pending'
    canceled = 'canceled'
    completed = 'completed'


class WebsetIdleEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.idle']
    data: Webset
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetItem(ExaBaseModel):
    id: str
    """
    The unique identifier for the Webset Item
    """
    object: Literal['webset_item']
    source: Source
    """
    The source of the Item
    """
    source_id: str = Field(..., alias='sourceId')
    """
    The unique identifier for the source
    """
    webset_id: str = Field(..., alias='websetId')
    """
    The unique identifier for the Webset this Item belongs to.
    """
    properties: Union[
        WebsetItemPersonProperties,
        WebsetItemCompanyProperties,
        WebsetItemArticleProperties,
        WebsetItemResearchPaperProperties,
        WebsetItemCustomProperties,
    ]
    """
    The properties of the Item
    """
    evaluations: List[WebsetItemEvaluation]
    """
    The criteria evaluations of the item
    """
    enrichments: List[EnrichmentResult]
    """
    The enrichments results of the Webset item
    """
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the item was created
    """
    updated_at: datetime = Field(..., alias='updatedAt')
    """
    The date and time the item was last updated
    """


class WebsetItemArticleProperties(ExaBaseModel):
    type: Literal['article']
    url: AnyUrl
    """
    The URL of the article
    """
    description: str
    """
    Short description of the relevance of the article
    """
    content: Optional[str] = None
    """
    The text content for the article
    """
    article: WebsetItemArticlePropertiesFields = Field(
        ..., title='WebsetItemArticlePropertiesFields'
    )


class WebsetItemArticlePropertiesFields(ExaBaseModel):
    author: Optional[str] = None
    """
    The author(s) of the article
    """
    published_at: Optional[str] = Field(..., alias='publishedAt')
    """
    The date and time the article was published
    """


class WebsetItemCompanyProperties(ExaBaseModel):
    type: Literal['company']
    url: AnyUrl
    """
    The URL of the company website
    """
    description: str
    """
    Short description of the relevance of the company
    """
    content: Optional[str] = None
    """
    The text content of the company website
    """
    company: WebsetItemCompanyPropertiesFields = Field(
        ..., title='WebsetItemCompanyPropertiesFields'
    )


class WebsetItemCompanyPropertiesFields(ExaBaseModel):
    name: str
    """
    The name of the company
    """
    location: Optional[str] = None
    """
    The main location of the company
    """
    employees: Optional[float] = None
    """
    The number of employees of the company
    """
    industry: Optional[str] = None
    """
    The industry of the company
    """
    about: Optional[str] = None
    """
    A short description of the company
    """
    logo_url: Optional[AnyUrl] = Field(..., alias='logoUrl')
    """
    The logo URL of the company
    """


class WebsetItemCreatedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.item.created']
    data: WebsetItem
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetItemCustomProperties(ExaBaseModel):
    type: Literal['custom']
    url: AnyUrl
    """
    The URL of the Item
    """
    description: str
    """
    Short description of the Item
    """
    content: Optional[str] = None
    """
    The text content of the Item
    """
    custom: WebsetItemCustomPropertiesFields = Field(
        ..., title='WebsetItemCustomPropertiesFields'
    )


class WebsetItemCustomPropertiesFields(ExaBaseModel):
    author: Optional[str] = None
    """
    The author(s) of the website
    """
    published_at: Optional[str] = Field(..., alias='publishedAt')
    """
    The date and time the website was published
    """


class WebsetItemEnrichedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.item.enriched']
    data: WebsetItem
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetItemEvaluation(ExaBaseModel):
    criterion: str
    """
    The description of the criterion
    """
    reasoning: str
    """
    The reasoning for the result of the evaluation
    """
    satisfied: Satisfied
    """
    The satisfaction of the criterion
    """
    references: List[Reference] = []
    """
    The references used to generate the result. `null` if the evaluation is not yet completed.
    """


class WebsetItemPersonProperties(ExaBaseModel):
    type: Literal['person']
    url: AnyUrl
    """
    The URL of the person profile
    """
    description: str
    """
    Short description of the relevance of the person
    """
    person: WebsetItemPersonPropertiesFields = Field(
        ..., title='WebsetItemPersonPropertiesFields'
    )


class WebsetItemPersonPropertiesFields(ExaBaseModel):
    name: str
    """
    The name of the person
    """
    location: Optional[str] = None
    """
    The location of the person
    """
    position: Optional[str] = None
    """
    The current work position of the person
    """
    picture_url: Optional[AnyUrl] = Field(..., alias='pictureUrl')
    """
    The image URL of the person
    """


class WebsetItemResearchPaperProperties(ExaBaseModel):
    type: Literal['research_paper']
    url: AnyUrl
    """
    The URL of the research paper
    """
    description: str
    """
    Short description of the relevance of the research paper
    """
    content: Optional[str] = None
    """
    The text content of the research paper
    """
    research_paper: WebsetItemResearchPaperPropertiesFields = Field(
        ..., alias='researchPaper', title='WebsetItemResearchPaperPropertiesFields'
    )


class WebsetItemResearchPaperPropertiesFields(ExaBaseModel):
    author: Optional[str] = None
    """
    The author(s) of the research paper
    """
    published_at: Optional[str] = Field(..., alias='publishedAt')
    """
    The date and time the research paper was published
    """


class WebsetPausedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.paused']
    data: Webset
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetPersonEntity(ExaBaseModel):
    type: Literal['person']


class WebsetResearchPaperEntity(ExaBaseModel):
    type: Literal['research_paper']


class WebsetSearch(ExaBaseModel):
    id: str
    """
    The unique identifier for the search
    """
    object: Literal['webset_search']
    status: WebsetSearchStatus = Field(..., title='WebsetSearchStatus')
    """
    The status of the search
    """
    query: constr(min_length=1)
    """
    The query used to create the search.
    """
    entity: Union[
        WebsetCompanyEntity,
        WebsetPersonEntity,
        WebsetArticleEntity,
        WebsetResearchPaperEntity,
        WebsetCustomEntity,
    ]
    """
    The entity the search will return results for.

    When no entity is provided during creation, we will automatically select the best entity based on the query.
    """
    criteria: List[Criterion]
    """
    The criteria the search will use to evaluate the results. If not provided, we will automatically generate them for you.
    """
    count: confloat(ge=1.0)
    """
    The number of results the search will attempt to find. The actual number of results may be less than this number depending on the search complexity.
    """
    progress: Progress
    """
    The progress of the search
    """
    metadata: Optional[Dict[str, Any]] = {}
    """
    Set of key-value pairs you want to associate with this object.
    """
    canceled_at: Optional[datetime] = Field(..., alias='canceledAt')
    """
    The date and time the search was canceled
    """
    canceled_reason: Optional[CanceledReason] = Field(..., alias='canceledReason')
    """
    The reason the search was canceled
    """
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the search was created
    """
    updated_at: datetime = Field(..., alias='updatedAt')
    """
    The date and time the search was updated
    """


class WebsetSearchBehaviour(Enum):
    """
    The behaviour of the Search when it is added to a Webset.

    - `override`: the search will reuse the existing Items found in the Webset and evaluate them against the new criteria. Any Items that don't match the new criteria will be discarded.
    """

    override = 'override'


class WebsetSearchCanceledEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.search.canceled']
    data: WebsetSearch
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetSearchCompletedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.search.completed']
    data: WebsetSearch
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetSearchCreatedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.search.created']
    data: WebsetSearch
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetSearchStatus(Enum):
    """
    The status of the search
    """

    created = 'created'
    running = 'running'
    completed = 'completed'
    canceled = 'canceled'


class WebsetSearchUpdatedEvent(ExaBaseModel):
    id: str
    """
    The unique identifier for the event
    """
    object: Literal['event']
    type: Literal['webset.search.updated']
    data: WebsetSearch
    created_at: datetime = Field(..., alias='createdAt')
    """
    The date and time the event was created
    """


class WebsetStatus(Enum):
    """
    The status of the webset
    """

    idle = 'idle'
    running = 'running'
    paused = 'paused'


class GetWebsetResponse(Webset):
    items: Optional[List[WebsetItem]] = None
    """
    When expand query parameter contains `items`, this will contain the items in the webset
    """