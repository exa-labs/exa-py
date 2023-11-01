import pytest
from metaphor_python.api import Result, filter
from dataclasses import asdict


@pytest.fixture
def sample_result():
    return [
        Result(title="New Title", url="https://www.sample.com",id=1, score=0.123, published_date="2023-10-7", author="Fahmi", extract="Extracted content"),
        Result(title="Lorem", url="https://www.sample.com", id=2, score=0.023, published_date="2023-10-7", author="Fahmi", extract="Extracted content"),
        Result(title="Ipsum", url="https://www.sample.com", id=3, score=0.003, published_date="2023-10-7", author="Fahmi", extract="Extracted content"),
    ]

def test_filter_result_score(sample_result):
    filtered_data = filter(input=sample_result, options=('score',))[0]
    for item in filtered_data:
        assert asdict(item) == {'title': item.title, 'url': item.url, 'id': item.id, 'score': item.score, 'published_date': None, 'author': None, 'extract': None}
    
def test_filter_result_score_published_date(sample_result):
    filtered_data = filter(input=sample_result, options=('score', 'published_date'))[0]
    for item in filtered_data:
        assert asdict(item) == {'title': item.title, 'url': item.url, 'id': item.id, 'score': item.score, 'published_date': item.published_date, 'author': None, 'extract': None}
    
def test_filter_result_score_published_date_author(sample_result):
    filtered_data = filter(input=sample_result, options=('score', 'published_date', 'author'))[0]
    for item in filtered_data:
        assert asdict(item) == {'title': item.title, 'url': item.url, 'id': item.id, 'score': item.score, 'published_date': item.published_date, 'author': item.author, 'extract': None}

